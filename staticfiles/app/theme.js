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
        const botao = document.createElement('button');
        botao.type = 'button';
        botao.className = 'theme-toggle';
        botao.addEventListener('click', function () {
            const tema = root.dataset.theme === 'dark' ? 'light' : 'dark';
            aplicarTema(tema);
            try {
                localStorage.setItem(storageKey, tema);
            } catch (error) {
                // Ignora somente a persistência quando ela não estiver disponível.
            }
        });
        document.body.appendChild(botao);
        aplicarTema(root.dataset.theme || temaInicial());
    });
})();
