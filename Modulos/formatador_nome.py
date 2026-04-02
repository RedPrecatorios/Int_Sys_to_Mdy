"""
Formatação de nomes para o padrão SMS.

Regra:
  - Primeiro nome  → completo (Title Case)
  - Nomes do meio  → apenas a inicial seguida de ponto (ex: N.)
  - Último nome    → completo (Title Case)

Exemplos:
  "FILIPE NOBERTO DA SILVA JUSTINO" → "Filipe N. D. S. Justino"
  "MARIA CLARA SANTOS"              → "Maria C. Santos"
  "JOSE SILVA"                      → "Jose Silva"
  "ANA"                             → "Ana"
"""


def formatar_nome_sms(nome: str) -> str:
    """
    Recebe um nome completo (qualquer caixa) e retorna no formato SMS:
    Primeiro <Iniciais do meio>. Último
    """
    if not nome or not nome.strip():
        return ""

    partes = nome.strip().split()

    if len(partes) == 1:
        return partes[0].capitalize()

    if len(partes) == 2:
        return f"{partes[0].capitalize()} {partes[1].capitalize()}"

    primeiro = partes[0].capitalize()
    ultimo   = partes[-1].capitalize()
    meio     = " ".join(f"{p[0].upper()}." for p in partes[1:-1])

    return f"{primeiro} {meio} {ultimo}"
