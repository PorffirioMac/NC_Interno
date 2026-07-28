(function () {
    const storageKey = 'meusistema-tema';
    const root = document.documentElement;

    function temaInicial() {
        try {
            const salvo = localStorage.getItem(storageKey);
            if (salvo === 'light' || salvo === 'dark') return salvo;
        } catch (error) {
            // O tema ainda funciona quando o armazenamento estiver bloqueado.
        }
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }

    function aplicarTema(tema) {
        root.dataset.theme = tema;
        const botao = document.querySelector('.theme-toggle');
        if (botao) {
            const escuro = tema === 'dark';
            botao.textContent = escuro ? '☀️' : '🌙';
            botao.title = escuro ? 'Ativar modo claro' : 'Ativar modo escuro';
            botao.setAttribute('aria-label', botao.title);
        }
    }

    aplicarTema(temaInicial());

    document.addEventListener('DOMContentLoaded', function () {
        let botao = document.querySelector('.theme-toggle');
        if (!botao) {
            botao = document.createElement('button');
            botao.type = 'button';
            botao.className = 'theme-toggle theme-toggle-floating';
            document.body.appendChild(botao);
        }
        botao.addEventListener('click', function () {
            const tema = root.dataset.theme === 'dark' ? 'light' : 'dark';
            aplicarTema(tema);
            try {
                localStorage.setItem(storageKey, tema);
            } catch (error) {
                // Ignora somente a persistência quando ela não estiver disponível.
            }
        });
        aplicarTema(root.dataset.theme || temaInicial());

        const loginForm = document.getElementById('loginForm');
        if (loginForm) {
            loginForm.addEventListener('submit', function () {
                try {
                    sessionStorage.setItem('ncinterno-som-apos-login', '1');
                } catch (error) {
                    // O aviso continua funcionando nas próximas atualizações.
                }
            });
        }

        const painel = document.getElementById('notificationPanel');
        if (!painel) return;

        const chavePainel = 'ncinterno-avisos-minimizado';
        const chavePosicao = 'ncinterno-avisos-posicao-y';
        const chavePosicaoMinimizada = 'ncinterno-avisos-posicao-y-minimizado';
        const toggle = document.getElementById('notificationToggle');
        const close = document.getElementById('notificationClose');
        const header = painel.querySelector('.notification-header');
        let arrastouToggle = false;

        function tocarAviso() {
            return new Promise(function (resolve, reject) {
                const AudioContext = window.AudioContext || window.webkitAudioContext;
                if (!AudioContext) {
                    reject(new Error('Áudio não suportado.'));
                    return;
                }
                try {
                    const contexto = new AudioContext();
                    function criarNota(frequencia, inicio, duracao, volume) {
                        const oscilador = contexto.createOscillator();
                        const ganho = contexto.createGain();
                        oscilador.type = 'sine';
                        oscilador.frequency.setValueAtTime(frequencia, inicio);
                        ganho.gain.setValueAtTime(0.0001, inicio);
                        ganho.gain.exponentialRampToValueAtTime(volume, inicio + 0.025);
                        ganho.gain.exponentialRampToValueAtTime(0.0001, inicio + duracao);
                        oscilador.connect(ganho);
                        ganho.connect(contexto.destination);
                        oscilador.start(inicio);
                        oscilador.stop(inicio + duracao);
                    }
                    function iniciar() {
                        const agora = contexto.currentTime + 0.03;
                        criarNota(659.25, agora, 0.22, 0.42);
                        criarNota(783.99, agora + 0.15, 0.30, 0.36);
                        window.setTimeout(function () {
                            contexto.close().finally(resolve);
                        }, 650);
                    }
                    if (contexto.state === 'suspended') {
                        contexto.resume().then(iniciar).catch(reject);
                    } else {
                        iniciar();
                    }
                } catch (error) {
                    reject(error);
                }
            });
        }

        let somPendente = false;
        function tocarOuAguardarInteracao() {
            tocarAviso().catch(function () {
                if (somPendente) return;
                somPendente = true;
                function tentarNovamente() {
                    document.removeEventListener('pointerdown', tentarNovamente);
                    document.removeEventListener('keydown', tentarNovamente);
                    somPendente = false;
                    tocarAviso().catch(function () {});
                }
                document.addEventListener('pointerdown', tentarNovamente, { once: true });
                document.addEventListener('keydown', tentarNovamente, { once: true });
            });
        }

        const usuarioId = painel.dataset.userId;
        const chaveAssinatura = 'ncinterno-avisos-assinatura-' + usuarioId;
        const chaveSessao = 'ncinterno-avisos-sessao-' + usuarioId;
        let assinaturaAtual = painel.dataset.unreadSignature || '0:0';
        let totalAtual = Number(painel.dataset.unreadCount || 0);

        function idsDaAssinatura(assinatura) {
            return String(assinatura).split(':').map(function (valor) {
                return Number(valor) || 0;
            });
        }

        function assinaturaTemNovidade(nova, anterior) {
            const idsNovos = idsDaAssinatura(nova);
            const idsAnteriores = idsDaAssinatura(anterior);
            return idsNovos.some(function (id, indice) {
                return id > (idsAnteriores[indice] || 0);
            });
        }

        try {
            const assinaturaSalva = localStorage.getItem(chaveAssinatura);
            const veioDoLogin = sessionStorage.getItem('ncinterno-som-apos-login') === '1';
            const primeiraPaginaDaSessao = sessionStorage.getItem(chaveSessao) !== '1';
            sessionStorage.removeItem('ncinterno-som-apos-login');
            sessionStorage.setItem(chaveSessao, '1');
            if (
                totalAtual > 0
                && (
                    veioDoLogin
                    || primeiraPaginaDaSessao
                    || (assinaturaSalva && assinaturaTemNovidade(assinaturaAtual, assinaturaSalva))
                )
            ) {
                window.setTimeout(tocarOuAguardarInteracao, 350);
            }
            localStorage.setItem(chaveAssinatura, assinaturaAtual);
        } catch (error) {
            // O acompanhamento em memória continua disponível.
        }

        let consultandoStatus = false;
        function consultarNovidades() {
            if (consultandoStatus || document.hidden) return;
            consultandoStatus = true;
            fetch(painel.dataset.statusUrl, {
                credentials: 'same-origin',
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                cache: 'no-store'
            })
                .then(function (resposta) {
                    if (!resposta.ok) throw new Error('Não foi possível consultar os avisos.');
                    return resposta.json();
                })
                .then(function (dados) {
                    const novaAssinatura = dados.assinatura || '0:0';
                    const novoTotal = Number(dados.total || 0);
                    if (
                        novoTotal > 0
                        && assinaturaTemNovidade(novaAssinatura, assinaturaAtual)
                    ) {
                        tocarOuAguardarInteracao();
                    }
                    assinaturaAtual = novaAssinatura;
                    totalAtual = novoTotal;
                    try {
                        localStorage.setItem(chaveAssinatura, assinaturaAtual);
                    } catch (error) {
                        // Mantém apenas o acompanhamento desta página.
                    }
                })
                .catch(function () {
                    // Falhas temporárias não interrompem a página.
                })
                .finally(function () {
                    consultandoStatus = false;
                });
        }
        window.setInterval(consultarNovidades, 20000);
        document.addEventListener('visibilitychange', consultarNovidades);

        function definirMinimizado(minimizado) {
            painel.classList.toggle('is-minimized', minimizado);
            if (toggle) toggle.setAttribute('aria-expanded', String(!minimizado));
            if (minimizado) aplicarPosicaoMinimizada();
            else aplicarPosicaoSalva();
            try {
                localStorage.setItem(chavePainel, minimizado ? '1' : '0');
            } catch (error) {
                // O painel continua funcional sem persistência local.
            }
        }

        try {
            definirMinimizado(localStorage.getItem(chavePainel) === '1');
        } catch (error) {
            definirMinimizado(false);
        }

        if (close) close.addEventListener('click', function () { definirMinimizado(true); });
        if (toggle) {
            toggle.addEventListener('click', function () {
                if (arrastouToggle) {
                    arrastouToggle = false;
                    return;
                }
                definirMinimizado(false);
            });
        }

        function limitarPosicao(top) {
            const margem = 8;
            const altura = painel.offsetHeight;
            const maximo = Math.max(margem, window.innerHeight - altura - margem);
            return Math.min(Math.max(top, margem), maximo);
        }

        function aplicarPosicaoSalva() {
            if (painel.classList.contains('is-minimized')) return;
            try {
                const salva = Number(localStorage.getItem(chavePosicao));
                if (Number.isFinite(salva) && salva > 0) {
                    painel.style.top = limitarPosicao(salva) + 'px';
                    painel.style.bottom = 'auto';
                } else {
                    painel.style.top = (window.innerWidth <= 700 ? 74 : 86) + 'px';
                    painel.style.bottom = 'auto';
                }
            } catch (error) {
                // Mantém a posição padrão quando o armazenamento estiver bloqueado.
            }
        }

        function aplicarPosicaoMinimizada() {
            if (!painel.classList.contains('is-minimized')) return;
            try {
                const salva = Number(localStorage.getItem(chavePosicaoMinimizada));
                if (Number.isFinite(salva) && salva > 0) {
                    painel.style.top = limitarPosicao(salva) + 'px';
                    painel.style.bottom = 'auto';
                } else {
                    painel.style.top = 'auto';
                    painel.style.bottom = '80px';
                }
            } catch (error) {
                painel.style.top = 'auto';
                painel.style.bottom = '80px';
            }
        }

        aplicarPosicaoSalva();

        if (header) {
            header.addEventListener('pointerdown', function (event) {
                if (event.target.closest('button')) return;
                event.preventDefault();
                const inicioY = event.clientY;
                const inicioTop = painel.getBoundingClientRect().top;
                painel.classList.add('is-dragging');
                header.setPointerCapture(event.pointerId);

                function mover(moveEvent) {
                    const top = limitarPosicao(inicioTop + moveEvent.clientY - inicioY);
                    painel.style.top = top + 'px';
                    painel.style.bottom = 'auto';
                }

                function finalizar() {
                    painel.classList.remove('is-dragging');
                    header.removeEventListener('pointermove', mover);
                    header.removeEventListener('pointerup', finalizar);
                    header.removeEventListener('pointercancel', finalizar);
                    try {
                        localStorage.setItem(
                            chavePosicao,
                            String(Math.round(painel.getBoundingClientRect().top))
                        );
                    } catch (error) {
                        // A movimentação continua funcional sem persistência.
                    }
                }

                header.addEventListener('pointermove', mover);
                header.addEventListener('pointerup', finalizar);
                header.addEventListener('pointercancel', finalizar);
            });
        }

        if (toggle) {
            toggle.addEventListener('pointerdown', function (event) {
                event.preventDefault();
                const inicioY = event.clientY;
                const inicioTop = painel.getBoundingClientRect().top;
                arrastouToggle = false;
                painel.classList.add('is-dragging');
                toggle.setPointerCapture(event.pointerId);

                function mover(moveEvent) {
                    if (Math.abs(moveEvent.clientY - inicioY) > 4) {
                        arrastouToggle = true;
                    }
                    if (!arrastouToggle) return;
                    const top = limitarPosicao(inicioTop + moveEvent.clientY - inicioY);
                    painel.style.top = top + 'px';
                    painel.style.bottom = 'auto';
                }

                function finalizar() {
                    painel.classList.remove('is-dragging');
                    toggle.removeEventListener('pointermove', mover);
                    toggle.removeEventListener('pointerup', finalizar);
                    toggle.removeEventListener('pointercancel', finalizar);
                    if (!arrastouToggle) return;
                    try {
                        localStorage.setItem(
                            chavePosicaoMinimizada,
                            String(Math.round(painel.getBoundingClientRect().top))
                        );
                    } catch (error) {
                        // A movimentação continua funcional sem persistência.
                    }
                }

                toggle.addEventListener('pointermove', mover);
                toggle.addEventListener('pointerup', finalizar);
                toggle.addEventListener('pointercancel', finalizar);
            });
        }

        window.addEventListener('resize', function () {
            painel.style.top = limitarPosicao(painel.getBoundingClientRect().top) + 'px';
            painel.style.bottom = 'auto';
        });

        function csrfToken() {
            const item = document.cookie.split('; ').find(function (cookie) {
                return cookie.startsWith('csrftoken=');
            });
            return item ? decodeURIComponent(item.split('=').slice(1).join('=')) : '';
        }

        function postar(url) {
            return fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken(),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin'
            });
        }

        painel.querySelectorAll('[data-read-url]').forEach(function (item) {
            item.addEventListener('click', function (event) {
                if (!item.classList.contains('unread')) return;
                event.preventDefault();
                postar(item.dataset.readUrl).finally(function () {
                    window.location.href = item.href;
                });
            });
        });

        const readAll = document.getElementById('notificationReadAll');
        if (readAll) {
            readAll.addEventListener('click', function () {
                postar(readAll.dataset.url).then(function (response) {
                    if (!response.ok) return;
                    painel.querySelectorAll('#notificationUpdates .notification-item.unread').forEach(function (item) {
                        item.classList.remove('unread');
                    });
                    readAll.remove();
                    const badge = document.getElementById('notificationBadge');
                    if (badge) {
                        const restantes = painel.querySelectorAll(
                            '.notification-item.deadline, .notification-item.communication.unread'
                        ).length;
                        if (restantes) badge.textContent = String(restantes);
                        else badge.remove();
                    }
                });
            });
        }
    });
})();
