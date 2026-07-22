from django import forms
import re

from .models import Cliente, ErroConhecido, Release, SolicitacaoRelease


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
            'versao_observada',
            'clientes',
            'ticket_netcontroll',
        ]
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 7}),
            'clientes': forms.CheckboxSelectMultiple(),
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
