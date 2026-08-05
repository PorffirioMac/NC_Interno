from django import forms
from django.contrib.auth.models import User
import re
from decimal import Decimal, InvalidOperation

from .models import (
    Cliente, DespesaFinanceira, ErroConhecido, ProcedimentoInterno, Release,
    Rotina, SolicitacaoRelease,
)


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            'codigo',
            'nome_fantasia',
            'razao_social',
            'cnpj',
            'proprietario',
            'telefone',
            'observacoes',
        ]
        widgets = {
            'codigo': forms.TextInput(attrs={
                'inputmode': 'numeric',
                'maxlength': '5',
                'placeholder': '00000',
                'autocomplete': 'off',
            }),
            'cnpj': forms.TextInput(attrs={
                'inputmode': 'numeric',
                'maxlength': '18',
                'placeholder': '00.000.000/0000-00',
                'autocomplete': 'off',
            }),
            'telefone': forms.TextInput(attrs={
                'inputmode': 'numeric',
                'maxlength': '15',
                'placeholder': '(00) 00000-0000',
                'autocomplete': 'tel',
            }),
            'observacoes': forms.Textarea(attrs={'rows': 6}),
        }

    def clean_codigo(self):
        codigo = self.cleaned_data.get('codigo', '').strip()
        if not re.fullmatch(r'\d{5}', codigo):
            raise forms.ValidationError('Digite uma ID com exatamente 5 números.')
        return codigo

    def clean_cnpj(self):
        numeros = re.sub(r'\D', '', self.cleaned_data['cnpj'])
        if len(numeros) != 14:
            raise forms.ValidationError('Digite os 14 números do CNPJ.')
        return (
            f'{numeros[:2]}.{numeros[2:5]}.{numeros[5:8]}/'
            f'{numeros[8:12]}-{numeros[12:]}'
        )

    def clean_telefone(self):
        numeros = re.sub(r'\D', '', self.cleaned_data['telefone'])
        if len(numeros) not in (10, 11):
            raise forms.ValidationError(
                'Digite o DDD e os 8 dígitos do telefone fixo ou os 9 dígitos do celular.'
            )
        if len(numeros) == 10:
            return f'({numeros[:2]}) {numeros[2:6]}-{numeros[6:]}'
        return f'({numeros[:2]}) {numeros[2:7]}-{numeros[7:]}'


class ErroConhecidoForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['clientes'].queryset = Cliente.objects.filter(ativo=True)

    class Meta:
        model = ErroConhecido
        fields = [
            'palavra_chave',
            'modulo',
            'descricao',
            'corrigido',
            'medida_corretiva',
            'versao_observada',
            'clientes',
            'ticket_netcontroll',
        ]
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 7}),
            'medida_corretiva': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Descreva o procedimento a aplicar quando o erro ocorrer.',
            }),
            'clientes': forms.CheckboxSelectMultiple(),
        }


class ProcedimentoInternoForm(forms.ModelForm):
    class Meta:
        model = ProcedimentoInterno
        fields = ['titulo', 'conteudo']
        widgets = {
            'titulo': forms.TextInput(attrs={
                'placeholder': 'Ex.: Instalação completa do PDV',
            }),
            'conteudo': forms.Textarea(attrs={
                'rows': 18,
                'placeholder': 'Descreva o procedimento do começo ao fim.',
            }),
        }


class ReleaseForm(forms.ModelForm):
    class Meta:
        model = Release
        fields = ['versao', 'titulo', 'conteudo']
        widgets = {'conteudo': forms.Textarea(attrs={'rows': 8})}


class SolicitacaoReleaseForm(forms.ModelForm):
    class Meta:
        model = SolicitacaoRelease
        fields = ['tipo', 'titulo', 'descricao']
        widgets = {'descricao': forms.Textarea(attrs={'rows': 5})}


class DespesaFinanceiraForm(forms.ModelForm):
    valor = forms.CharField(
        label='Valor mensal',
        widget=forms.TextInput(attrs={
            'inputmode': 'decimal',
            'placeholder': '0,00',
        }),
    )

    class Meta:
        model = DespesaFinanceira
        fields = ['titulo', 'valor', 'dia_vencimento', 'descricao']
        widgets = {
            'titulo': forms.TextInput(attrs={'placeholder': 'Ex.: Aluguel'}),
            'dia_vencimento': forms.NumberInput(attrs={'min': 1, 'max': 31}),
            'descricao': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Informações adicionais (opcional)',
            }),
        }

    def clean_valor(self):
        texto = self.cleaned_data['valor'].strip().replace(' ', '')
        if ',' in texto:
            texto = texto.replace('.', '').replace(',', '.')
        try:
            valor = Decimal(texto)
        except InvalidOperation as error:
            raise forms.ValidationError('Informe um valor válido.') from error
        if valor <= 0:
            raise forms.ValidationError('O valor deve ser maior que zero.')
        return valor


class RotinaForm(forms.ModelForm):
    class Meta:
        model = Rotina
        fields = [
            'titulo', 'responsavel', 'periodicidade', 'dia_mes', 'descricao',
        ]
        widgets = {
            'titulo': forms.TextInput(attrs={
                'placeholder': 'Ex.: Conferir chamados pendentes',
            }),
            'dia_mes': forms.NumberInput(attrs={'min': 1, 'max': 31}),
            'descricao': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Orientações para realizar a tarefa (opcional)',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['responsavel'].queryset = User.objects.filter(
            is_active=True,
        ).order_by('first_name', 'username')
        self.fields['dia_mes'].required = False

    def clean(self):
        dados = super().clean()
        periodicidade = dados.get('periodicidade')
        dia_mes = dados.get('dia_mes')
        if periodicidade == 'mensal' and not dia_mes:
            self.add_error(
                'dia_mes',
                'Informe o dia em que a rotina mensal deve aparecer.',
            )
        if periodicidade != 'mensal':
            dados['dia_mes'] = None
        return dados
