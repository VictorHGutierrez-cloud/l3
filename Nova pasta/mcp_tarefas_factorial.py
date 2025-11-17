#!/usr/bin/env python3
"""
MCP Tarefas Factorial - Servidor MCP completo para processar transcrições
e gerenciar tarefas do Victor Gutierrez na Factorial.

Configurações pré-configuradas:
- Email: victor.gutierrez@factorial.co
- Calendário: victorgutierrez759@gmail.com
- Busca tarefas atribuídas ao "Victor"
"""

import asyncio
import json
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Any, List, Dict, Optional
from pathlib import Path

# Importações do Google Calendar
try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from google.auth.transport.requests import Request
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

# Importações do MCP SDK
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("⚠️  MCP SDK não instalado. Execute: pip install mcp")
    print("   O servidor ainda funciona como script Python normal.")

# ============================================================================
# CONFIGURAÇÕES PRÉ-DEFINIDAS - MCP TAREFAS FACTORIAL
# ============================================================================

CONFIG = {
    "email": {
        "destinatario": "victor.gutierrez@factorial.co",
        "nome": "Victor",
        "smtp_user": "victor.gutierrez@factorial.co",
        "smtp_pass": "wglzlzyggeeivwmy",
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 465
    },
    "calendario": {
        "email_conta": "victorgutierrez759@gmail.com",
        "credentials_file": "client_secret_2_333464808778-ar96u1mn7q3ug5et2qvf1v5j7vctat25.apps.googleusercontent.com.json",
        "token_file": "credenciais_google.json"
    },
    "padroes": {
        "nome_pessoa": "victor",
        "timezone": "America/Sao_Paulo"
    }
}

# Padrões de identificação de tarefas
PADROES_ATRIBUICAO_DIRETA = [
    r'victor[,:]?\s+(?:você\s+)?(?:pode|poderia|consegue)\s+(?:fazer|preparar|enviar|criar|desenvolver)',
    r'victor[,:]?\s+(?:você\s+)?(?:precisa|deve|tem que|vai ter que)\s+(?:fazer|preparar|enviar|criar)',
    r'(?:pede|peço|pediu)\s+(?:pro|para o?)\s+victor',
    r'victor\s+(?:fica|vai ficar)\s+responsável',
    r'victor[,:]?\s+(?:faz|faça|prepare|envie|crie|desenvolva)',
    r'(?:tem como|consegue|poderia|pode)\s+(?:você\s+)?(?:enviar|mandar|fazer|preparar|criar)',
    r'(?:você\s+)?(?:envia|manda|faz|prepara|cria).*(?:pra|para)\s+(?:mim|gente|nós)',
]

# Padrões de COMPROMISSOS ASSUMIDOS pelo Victor (não são atribuições diretas, mas ele assume)
PADROES_COMPROMISSO = [
    r'(?:vou|eu vou)\s+(?:te\s+)?(?:passar|enviar|mandar|fazer|preparar|criar|desenvolver)',
    r'(?:posso|pode)\s+(?:te\s+)?(?:enviar|mandar|passar|fazer)',
    r'(?:segunda|terça|quarta|quinta|sexta|sábado|domingo|hoje|amanhã).*(?:vou|eu vou|te passo|te envio|te mando)',
    r'(?:vou|eu vou)\s+(?:te\s+)?(?:passar|enviar|mandar).*(?:segunda|terça|quarta|quinta|sexta|sábado|domingo|hoje|amanhã)',
    r'(?:então|então,)\s+(?:segunda|terça|quarta|quinta|sexta|sábado|domingo).*(?:vou|eu vou|te passo|te envio)',
    r'(?:segunda|terça|quarta|quinta|sexta|sábado|domingo).*(?:eu\s+)?(?:te passo|te envio|te mando)',
    r'(?:vou|eu vou)\s+marcar',
    r'(?:vou|eu vou)\s+colocar',
    r'(?:combinado|ok|beleza|tá bom).*(?:vou|eu vou)',
    r'posso\s+te\s+enviar',  # "posso te enviar essa proposta"
    r'vou\s+te\s+passar',  # "vou te passar essa proposta"
]

PADROES_DEADLINE = [
    r'(?:até|para|antes de?)\s+(?:dia\s+)?(\d{1,2})\s*(?:de\s+)?(\w+)?',
    r'(?:até|para)\s+(?:o\s+)?(?:dia\s+)?(\d{1,2})',  # "até dia sete", "até o dia 7"
    r'(?:até|para)\s+(segunda|terça|quarta|quinta|sexta|sábado|domingo)(?:\s*-?\s*feira)?',
    r'(?:até|para)\s+(hoje|amanhã|depois de amanhã)',
    r'(?:prazo|deadline)[:\s]+([^\n.,;]+)',
    r'(?:às|as)\s+(\d{1,2})[h:]?(\d{2})?',
    r'(?:hoje|amanhã)\s+às\s+(\d{1,2})[h:]?(\d{2})?',
    r'(?:em|dentro de)\s+(\d+)\s+(dia|dias|semana|semanas|mês|meses)',
    r'(?:final|fim)\s+(?:de|da)\s+(semana|mês)',
    r'(?:semana|mês)\s+que\s+vem',
    r'primeira\s+semana\s+de\s+(\w+)',  # "primeira semana de novembro"
    r'semana\s+que\s+vem',  # "semana que vem"
    r'(?:início|começo)\s+(?:de|do|da)\s+(\w+)',  # "início de novembro"
]

PADROES_IGNORAR = [
    r'vai\s+(?:ser|estar|ficar|aparecer|trazer|mostrar|enxergar)',
    r'(?:vou|você vai)\s+(?:adorar|gostar|amar|ver|notar|entender|perceber)',
    r'pode\s+(?:ser|estar|fazer|ter)',
    r'tem\s+(?:que|como|os|as|isso|essa|esse)',
    r'vai\s+(?:dar|ter|aparecer)',
    r'(?:eu|a gente)\s+vai',
    r'(?:eu|a gente)\s+(?:vou|vamos)',
    r'você\s+(?:já|não|tem)',
    r'tá\s+(?:bom|bem|legal|perfeito)',
    r'vai\s+(?:precisar|poder|conseguir)',
]

# Verbos de ação para caracterizar tarefas reais (lista branca)
VERBOS_TAREFAS = [
    'enviar', 'mandar', 'passar',
    'marcar', 'agendar',
    'fechar', 'aprovar',
    'apresentar',
    'retornar', 'retorno', 'voltar',
    'começar', 'iniciar', 'implementar'
]

# Padrões que indicam fala sobre recursos/produto (para filtrar)
PADROES_RECURSOS_SISTEMA = [
    r'\bfactorial\b.*\btem\b',
    r'\bgestão de\b',
    r'\bintegra(?:ção|)\b',
    r'\bmódulo(?:s)?\b',
    r'\bposso\b\s+(?:fazer|criar|colocar|avaliar|emitir)',
    r'\bfaz(?:emos|)\b',
    r'\bconsegue\b\s+(?:fazer|emitir|assistir)',
    r'\bprojeto(?:s)?\b.*\btarefa(?:s)?\b',
    r'\bcertificado(?:s)?\b',
    r'\brelatório(?:s)?\b',
]


# ============================================================================
# CLASSE EXTRATOR DE TAREFAS
# ============================================================================

class ExtratorTarefasFactorial:
    """Extrai tarefas atribuídas ao Victor da Factorial"""
    
    def __init__(self, texto_reuniao: str):
        self.texto = texto_reuniao
        self.linhas = texto_reuniao.split('\n')
        self.tarefas = []
        self.data_reuniao = self._extrair_data_reuniao()
    
    def _extrair_data_reuniao(self) -> datetime:
        """Tenta extrair a data da reunião do texto"""
        # Procura por padrões como "dia 24", "estamos no dia X"
        for linha in self.linhas[-50:]:  # Procura nas últimas 50 linhas
            match = re.search(r'(?:estamos|está|estamos)\s+(?:no\s+)?dia\s+(\d{1,2})', linha.lower())
            if match:
                dia = int(match.group(1))
                hoje = datetime.now()
                # Se o dia mencionado já passou este mês, assume próximo mês
                if dia < hoje.day:
                    # Próximo mês
                    if hoje.month == 12:
                        return datetime(hoje.year + 1, 1, dia)
                    else:
                        return datetime(hoje.year, hoje.month + 1, dia)
                else:
                    return datetime(hoje.year, hoje.month, dia)
        return datetime.now()
    
    def extrair_deadline(self, texto: str, contexto_linhas: List[str]) -> Optional[Dict]:
        """Extrai deadline/prazo do texto"""
        texto_completo = texto + " " + " ".join(contexto_linhas)
        texto_lower = texto_completo.lower()
        
        dias_semana = {
            'segunda': 0, 'segunda-feira': 0,
            'terça': 1, 'terca': 1, 'terça-feira': 1, 'terca-feira': 1,
            'quarta': 2, 'quarta-feira': 2,
            'quinta': 3, 'quinta-feira': 3,
            'sexta': 4, 'sexta-feira': 4,
            'sábado': 5, 'sabado': 5,
            'domingo': 6
        }
        
        meses = {
            'janeiro': 1, 'fevereiro': 2, 'março': 3, 'marco': 3,
            'abril': 4, 'maio': 5, 'junho': 6,
            'julho': 7, 'agosto': 8, 'setembro': 9,
            'outubro': 10, 'novembro': 11, 'dezembro': 12
        }
        
        if re.search(r'\bhoje\b', texto_lower):
            return {'data': self.data_reuniao.date(), 'texto_original': 'hoje', 'horario': None}
        
        if re.search(r'\bamanhã\b', texto_lower):
            return {'data': (self.data_reuniao + timedelta(days=1)).date(), 'texto_original': 'amanhã', 'horario': None}
        
        for dia_nome, dia_num in dias_semana.items():
            if re.search(rf'\b{dia_nome}\b', texto_lower):
                dias_ate = (dia_num - self.data_reuniao.weekday()) % 7
                if dias_ate == 0:
                    dias_ate = 7
                data_deadline = self.data_reuniao + timedelta(days=dias_ate)
                return {'data': data_deadline.date(), 'texto_original': dia_nome, 'horario': None}
        
        # Melhorado: "até dia sete", "até o dia 7"
        match = re.search(r'(?:até|para)\s+(?:o\s+)?(?:dia\s+)?(\d{1,2})(?:\s+de\s+(\w+))?', texto_lower)
        if match:
            dia = int(match.group(1))
            mes_nome = match.group(2)
            
            if mes_nome and mes_nome in meses:
                mes = meses[mes_nome]
                ano = self.data_reuniao.year
                if mes < self.data_reuniao.month:
                    ano += 1
            else:
                # Sem mês especificado, assume mês atual ou próximo
                mes = self.data_reuniao.month
                ano = self.data_reuniao.year
                if dia < self.data_reuniao.day:
                    mes += 1
                    if mes > 12:
                        mes = 1
                        ano += 1
            
            try:
                data_deadline = datetime(ano, mes, dia).date()
                return {'data': data_deadline, 'texto_original': match.group(0), 'horario': None}
            except ValueError:
                pass
        
        # "primeira semana de novembro"
        match = re.search(r'primeira\s+semana\s+de\s+(\w+)', texto_lower)
        if match:
            mes_nome = match.group(1)
            if mes_nome in meses:
                mes = meses[mes_nome]
                ano = self.data_reuniao.year
                if mes < self.data_reuniao.month:
                    ano += 1
                # Primeira semana = dia 1 a 7, usa dia 7 como deadline
                try:
                    data_deadline = datetime(ano, mes, 7).date()
                    return {'data': data_deadline, 'texto_original': match.group(0), 'horario': None}
                except ValueError:
                    pass
        
        # "semana que vem"
        if re.search(r'semana\s+que\s+vem', texto_lower):
            # Próxima segunda-feira
            dias_ate_segunda = (0 - self.data_reuniao.weekday()) % 7
            if dias_ate_segunda == 0:
                dias_ate_segunda = 7
            data_deadline = (self.data_reuniao + timedelta(days=dias_ate_segunda + 6)).date()  # Final da semana
            return {'data': data_deadline, 'texto_original': 'semana que vem', 'horario': None}
        
        match = re.search(r'(?:em|dentro de)\s+(\d+)\s+(dia|dias|semana|semanas)', texto_lower)
        if match:
            quantidade = int(match.group(1))
            unidade = match.group(2)
            dias = quantidade * 7 if 'semana' in unidade else quantidade
            data_deadline = (self.data_reuniao + timedelta(days=dias)).date()
            return {'data': data_deadline, 'texto_original': match.group(0), 'horario': None}
        
        match = re.search(r'(?:às|as)\s+(\d{1,2})[h:]?(\d{2})?', texto_lower)
        if match:
            hora = int(match.group(1))
            minuto = int(match.group(2)) if match.group(2) else 0
            data_base = self.data_reuniao.date()
            return {'data': data_base, 'texto_original': match.group(0), 'horario': f'{hora:02d}:{minuto:02d}'}
        
        return None
    
    def e_atribuicao_direta(self, linha: str) -> bool:
        """Verifica se é atribuição direta ao Victor"""
        linha_lower = linha.lower()
        
        if re.search(r'^[^:]*victor[^:]*:', linha_lower):
            confirmacoes = [
                r'(?:ok|certo|sim|beleza)[,.]?\s+(?:vou|eu vou)\s+(?:fazer|preparar|enviar|criar|mandar)',
                r'(?:vou|eu vou)\s+(?:fazer|preparar|enviar|criar|desenvolver|mandar)',
                r'posso\s+fazer',
                r'faço\s+sim',
                r'(?:te|vou)\s+(?:mandar|enviar|passar).*(?:hoje|amanhã|agora)',
                r'(?:mando|envio)\s+(?:ainda\s+)?(?:hoje|amanhã)',
            ]
            for padrao in confirmacoes:
                if re.search(padrao, linha_lower):
                    return True
            return False
        
        for padrao in PADROES_ATRIBUICAO_DIRETA:
            if re.search(padrao, linha_lower):
                for padrao_ignorar in PADROES_IGNORAR:
                    if re.search(padrao_ignorar, linha_lower):
                        return False
                return True
        
        return False
    
    def e_compromisso_assumido(self, linha: str) -> bool:
        """Verifica se o Victor assumiu um compromisso (mesmo sem atribuição explícita)"""
        linha_lower = linha.lower()
        
        # Deve ser do Victor falando (melhorado para pegar "Victor Henrique..." ou só "Victor")
        if not re.search(r'victor[^:]*:', linha_lower):
            return False
        
        # Verifica padrões de compromisso
        for padrao in PADROES_COMPROMISSO:
            if re.search(padrao, linha_lower):
                # Verifica se não é um padrão a ignorar
                for padrao_ignorar in PADROES_IGNORAR:
                    if re.search(padrao_ignorar, linha_lower):
                        return False
                return True
        
        return False
    
    def e_compromisso_cliente(self, linha: str) -> bool:
        """Verifica se a cliente assumiu um compromisso com ação/prazo"""
        linha_lower = linha.lower()
        if not re.search(r'fabiana[^:]*:', linha_lower):
            return False
        padroes_cliente = [
            r'(?:vou|eu vou)\s+(?:fechar|apresentar|enviar|mandar|retornar|voltar)',
            r'(?:preciso|precisamos)\s+(?:fechar|apresentar|enviar|retornar|voltar)',
            r'\bfechar\b.*\bsemana\b',
            r'\bapresentar\b.*\bprimeira semana\b',
            r'\baté\b\s+(?:o\s+)?dia\s+\d{1,2}',
        ]
        for padrao in padroes_cliente:
            if re.search(padrao, linha_lower):
                return True
        return False
    
    def parece_acao(self, linha: str, contexto_linhas: List[str]) -> bool:
        """Retorna True se a linha/contexto aparenta descrever uma ação (não recurso/produto)"""
        texto = (linha + " " + " ".join(contexto_linhas)).lower()
        for padrao in PADROES_RECURSOS_SISTEMA:
            if re.search(padrao, texto):
                return False
        for verbo in VERBOS_TAREFAS:
            if re.search(rf'\b{verbo}\b', texto):
                return True
        return False
    
    def limpar_texto(self, texto: str) -> str:
        """Limpa o texto da tarefa"""
        texto = re.sub(r'^\d{1,2}:\d{2}(?::\d{2})?\s*[-–]\s*', '', texto).strip()
        texto = re.sub(r'^[^:]+:\s*', '', texto).strip()
        texto = re.sub(r'^[\s\-\*\•\d\.\)]+', '', texto).strip()
        if texto:
            texto = texto[0].upper() + texto[1:]
        return texto
    
    def obter_contexto(self, index: int, janela: int = 3) -> List[str]:
        """Obtém contexto ao redor da tarefa"""
        inicio = max(0, index - janela)
        fim = min(len(self.linhas), index + janela + 1)
        contexto = []
        for i in range(inicio, fim):
            if i != index and self.linhas[i].strip():
                linha_limpa = self.limpar_texto(self.linhas[i].strip())
                if linha_limpa and len(linha_limpa) > 10:
                    contexto.append(linha_limpa)
        return contexto
    
    def _extrair_tarefa_do_contexto(self, linha: str, contexto_linhas: List[str]) -> Optional[str]:
        """Tenta extrair a tarefa específica do contexto"""
        texto_completo = (linha + " " + " ".join(contexto_linhas)).lower()
        
        # Procura por palavras-chave de tarefas comuns (ordem importa!)
        if 'proposta' in texto_completo or 'orçamento' in texto_completo:
            return 'Enviar proposta comercial'
        if 'marcar' in texto_completo or 'agendar' in texto_completo or 'agenda' in texto_completo:
            return 'Marcar retorno/follow-up na agenda'
        if 'implementação' in texto_completo or 'implementar' in texto_completo:
            return 'Iniciar implementação'
        if 'retorno' in texto_completo or 'voltar a falar' in texto_completo or 'follow-up' in texto_completo:
            return 'Fazer retorno/follow-up'
        if 'enviar' in texto_completo or 'mandar' in texto_completo or 'passar' in texto_completo:
            # Tenta ser mais específico
            if 'proposta' in texto_completo:
                return 'Enviar proposta comercial'
            if 'orçamento' in texto_completo:
                return 'Enviar orçamento'
            return 'Enviar documento/informação'
        
        return None
    
    def extrair_tarefas(self) -> List[Dict[str, Any]]:
        """Extrai todas as tarefas atribuídas ao Victor (incluindo compromissos assumidos)"""
        tarefas_encontradas = []
        
        for index, linha in enumerate(self.linhas):
            linha_original = linha.strip()
            
            if not linha_original or len(linha_original) < 15:
                continue
            
            # Verifica atribuições diretas
            if self.e_atribuicao_direta(linha_original):
                tarefa_limpa = self.limpar_texto(linha_original)
                
                if tarefa_limpa and len(tarefa_limpa) > 10:
                    contexto_linhas = self.obter_contexto(index, janela=5)
                    if not self.parece_acao(linha_original, contexto_linhas):
                        continue
                    contexto_texto = ' | '.join(contexto_linhas[:3]) if contexto_linhas else ''
                    deadline_info = self.extrair_deadline(tarefa_limpa, contexto_linhas)
                    
                    tarefa = {
                        'texto': tarefa_limpa,
                        'linha_original': index + 1,
                        'contexto': contexto_texto,
                        'deadline': deadline_info,
                        'tipo': 'atribuicao_direta',
                        'responsavel': 'vendedor'
                    }
                    tarefas_encontradas.append(tarefa)
            
            # Verifica compromissos assumidos pelo Victor
            elif self.e_compromisso_assumido(linha_original):
                contexto_linhas = self.obter_contexto(index, janela=8)  # Janela maior para pegar mais contexto
                
                # Tenta extrair tarefa específica do contexto
                tarefa_especifica = self._extrair_tarefa_do_contexto(linha_original, contexto_linhas)
                
                if tarefa_especifica:
                    tarefa_limpa = tarefa_especifica
                else:
                    tarefa_limpa = self.limpar_texto(linha_original)
                
                if tarefa_limpa and len(tarefa_limpa) > 10:
                    if not self.parece_acao(linha_original, contexto_linhas) and not tarefa_especifica:
                        continue
                    contexto_texto = ' | '.join(contexto_linhas[:3]) if contexto_linhas else ''
                    
                    # Procura deadline na linha atual
                    deadline_info = self.extrair_deadline(tarefa_limpa, contexto_linhas)
                    
                    # Se não encontrou, procura no contexto expandido (linhas próximas)
                    if not deadline_info:
                        # Pega mais linhas ao redor para procurar deadlines
                        inicio = max(0, index - 5)
                        fim = min(len(self.linhas), index + 5)
                        linhas_contexto_expandido = []
                        for i in range(inicio, fim):
                            if i != index and self.linhas[i].strip():
                                linhas_contexto_expandido.append(self.linhas[i].strip())
                        texto_contexto_expandido = ' '.join(linhas_contexto_expandido)
                        deadline_info = self.extrair_deadline(texto_contexto_expandido, [])
                    
                    tarefa = {
                        'texto': tarefa_limpa,
                        'linha_original': index + 1,
                        'contexto': contexto_texto,
                        'deadline': deadline_info,
                        'tipo': 'compromisso_assumido',
                        'responsavel': 'vendedor'
                    }
                    tarefas_encontradas.append(tarefa)
            
            # Verifica compromissos assumidos pela cliente
            elif self.e_compromisso_cliente(linha_original):
                contexto_linhas = self.obter_contexto(index, janela=8)
                tarefa_especifica = self._extrair_tarefa_do_contexto(linha_original, contexto_linhas)
                if tarefa_especifica:
                    tarefa_limpa = tarefa_especifica
                else:
                    tarefa_limpa = self.limpar_texto(linha_original)
                
                if tarefa_limpa and len(tarefa_limpa) > 10:
                    if not self.parece_acao(linha_original, contexto_linhas) and not tarefa_especifica:
                        continue
                    contexto_texto = ' | '.join(contexto_linhas[:3]) if contexto_linhas else ''
                    
                    deadline_info = self.extrair_deadline(tarefa_limpa, contexto_linhas)
                    if not deadline_info:
                        inicio = max(0, index - 5)
                        fim = min(len(self.linhas), index + 5)
                        linhas_contexto_expandido = []
                        for i in range(inicio, fim):
                            if i != index and self.linhas[i].strip():
                                linhas_contexto_expandido.append(self.linhas[i].strip())
                        texto_contexto_expandido = ' '.join(linhas_contexto_expandido)
                        deadline_info = self.extrair_deadline(texto_contexto_expandido, [])
                    
                    tarefa = {
                        'texto': tarefa_limpa,
                        'linha_original': index + 1,
                        'contexto': contexto_texto,
                        'deadline': deadline_info,
                        'tipo': 'compromisso_cliente',
                        'responsavel': 'cliente'
                    }
                    tarefas_encontradas.append(tarefa)
        
        # Remove duplicatas
        tarefas_unicas = []
        textos_vistos = set()
        for tarefa in tarefas_encontradas:
            texto_normalizado = re.sub(r'\s+', ' ', tarefa['texto'].lower().strip())
            # Normaliza mais para evitar duplicatas similares
            texto_chave = re.sub(r'[^\w\s]', '', texto_normalizado)
            if texto_chave not in textos_vistos:
                textos_vistos.add(texto_chave)
                tarefas_unicas.append(tarefa)
        
        self.tarefas = tarefas_unicas
        return tarefas_unicas


# ============================================================================
# FUNÇÕES DE PROCESSAMENTO
# ============================================================================

def processar_transcricao(texto_transcricao: str) -> Dict[str, Any]:
    """Processa uma transcrição e extrai tarefas do Victor"""
    extrator = ExtratorTarefasFactorial(texto_transcricao)
    tarefas = extrator.extrair_tarefas()
    
    return {
        'tarefas': tarefas,
        'total': len(tarefas),
        'com_deadline': len([t for t in tarefas if t.get('deadline')]),
        'sem_deadline': len([t for t in tarefas if not t.get('deadline')])
    }


def enviar_email_tarefas(tarefas: List[Dict], assunto: str = None) -> Dict[str, Any]:
    """Envia email com tarefas para victor.gutierrez@factorial.co"""
    email_config = CONFIG['email']
    
    if not assunto:
        assunto = f"📋 Tarefas Factorial - {len(tarefas)} tarefa(s) - {datetime.now().strftime('%d/%m/%Y')}"
    
    # Gera HTML do email
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }}
            .tarefa {{ background: #f5f5f5; padding: 15px; margin: 10px 0; border-left: 4px solid #3498db; border-radius: 4px; }}
            .deadline {{ background: #fff3cd; padding: 10px; margin: 10px 0; font-weight: bold; border-radius: 4px; }}
            .deadline-urgente {{ background: #ffebee; border-left: 4px solid #e74c3c; }}
            h1 {{ color: #2c3e50; }}
        </style>
    </head>
    <body>
        <h1>📋 Suas Tarefas da Reunião - Factorial</h1>
        <p><strong>Processado em:</strong> {datetime.now().strftime('%d/%m/%Y às %H:%M')}</p>
        <p><strong>Total de tarefas:</strong> {len(tarefas)}</p>
    """
    
    for i, tarefa in enumerate(tarefas, 1):
        html += f"<div class='tarefa'><strong>{i}. {tarefa['texto']}</strong>"
        if tarefa.get('deadline'):
            d = tarefa['deadline']
            dias_restantes = (d['data'] - datetime.now().date()).days
            urgente = 'deadline-urgente' if dias_restantes <= 3 else ''
            horario = f" às {d['horario']}" if d.get('horario') else ""
            html += f"<div class='deadline {urgente}'>⏰ Deadline: {d['data']}{horario} ({dias_restantes} dias restantes)</div>"
        html += "</div>"
    
    html += """
        <hr>
        <p style="color: #7f8c8d; font-size: 12px;">
            🤖 Email gerado automaticamente pelo MCP Tarefas Factorial<br>
            Tarefas com deadline foram adicionadas ao Google Calendar
        </p>
    </body>
    </html>
    """
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = assunto
        msg['From'] = email_config['smtp_user']
        msg['To'] = email_config['destinatario']
        
        parte_html = MIMEText(html, 'html', 'utf-8')
        msg.attach(parte_html)
        
        with smtplib.SMTP_SSL(email_config['smtp_server'], email_config['smtp_port']) as server:
            server.login(email_config['smtp_user'], email_config['smtp_pass'])
            server.send_message(msg)
        
        return {'sucesso': True, 'mensagem': f'Email enviado para {email_config["destinatario"]}'}
    except Exception as e:
        return {'sucesso': False, 'erro': str(e)}


def criar_eventos_calendario(tarefas: List[Dict]) -> Dict[str, Any]:
    """Cria eventos no Google Calendar para tarefas com deadline"""
    if not GOOGLE_AVAILABLE:
        return {'sucesso': False, 'erro': 'Bibliotecas do Google não instaladas'}
    
    calendario_config = CONFIG['calendario']
    tarefas_com_deadline = [t for t in tarefas if t.get('deadline')]
    
    if not tarefas_com_deadline:
        return {'sucesso': True, 'mensagem': 'Nenhuma tarefa com deadline', 'eventos_criados': 0}
    
    base_path = Path(__file__).parent
    creds_file = base_path / calendario_config['token_file']
    
    if not creds_file.exists():
        return {'sucesso': False, 'erro': 'Credenciais do Google Calendar não configuradas. Execute configurar_google_calendar.py primeiro'}
    
    try:
        creds = Credentials.from_authorized_user_file(
            str(creds_file), 
            ['https://www.googleapis.com/auth/calendar']
        )
        
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                return {'sucesso': False, 'erro': 'Credenciais expiradas. Execute configurar_google_calendar.py novamente'}
        
        service = build('calendar', 'v3', credentials=creds)
        eventos_criados = 0
        
        for tarefa in tarefas_com_deadline:
            deadline = tarefa['deadline']
            data_deadline = deadline['data']
            
            evento = {
                'summary': f'📋 {tarefa["texto"][:100]}',
                'description': f'Tarefa da reunião Factorial:\n\n{tarefa["texto"]}\n\nContexto: {tarefa.get("contexto", "N/A")}',
                'start': {'date': data_deadline.isoformat()},
                'end': {'date': data_deadline.isoformat()},
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': 24 * 60},  # 1 dia antes
                        {'method': 'popup', 'minutes': 60},       # 1 hora antes
                    ],
                },
            }
            
            if deadline.get('horario'):
                hora, minuto = deadline['horario'].split(':')
                datetime_inicio = datetime.combine(
                    data_deadline, 
                    datetime.min.time().replace(hour=int(hora), minute=int(minuto))
                )
                datetime_fim = datetime_inicio + timedelta(hours=1)
                evento['start'] = {
                    'dateTime': datetime_inicio.isoformat(), 
                    'timeZone': CONFIG['padroes']['timezone']
                }
                evento['end'] = {
                    'dateTime': datetime_fim.isoformat(), 
                    'timeZone': CONFIG['padroes']['timezone']
                }
            
            service.events().insert(calendarId='primary', body=evento).execute()
            eventos_criados += 1
        
        return {'sucesso': True, 'mensagem': f'{eventos_criados} evento(s) criado(s) no calendário {calendario_config["email_conta"]}', 'eventos_criados': eventos_criados}
    except Exception as e:
        return {'sucesso': False, 'erro': str(e)}


# ============================================================================
# SERVIDOR MCP
# ============================================================================

if MCP_AVAILABLE:
    app = Server("mcp-tarefas-factorial")

    @app.list_tools()
    async def list_tools() -> list[Tool]:
        """Lista todas as ferramentas disponíveis"""
        return [
            Tool(
                name="processar_transcricao_factorial",
                description="Processa uma transcrição de reunião e extrai tarefas atribuídas ao Victor Gutierrez da Factorial. Já configurado com email victor.gutierrez@factorial.co e calendário victorgutierrez759@gmail.com",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "texto_transcricao": {
                            "type": "string",
                            "description": "Texto completo da transcrição da reunião"
                        }
                    },
                    "required": ["texto_transcricao"]
                }
            ),
            Tool(
                name="processar_e_enviar_completo_factorial",
                description="Processa transcrição, extrai tarefas do Victor, envia email para victor.gutierrez@factorial.co e cria eventos no Google Calendar (victorgutierrez759@gmail.com) - tudo de uma vez",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "texto_transcricao": {
                            "type": "string",
                            "description": "Texto completo da transcrição da reunião"
                        }
                    },
                    "required": ["texto_transcricao"]
                }
            )
        ]

    @app.call_tool()
    async def call_tool(name: str, arguments: Any) -> list[TextContent]:
        """Executa uma ferramenta do MCP"""
        
        if name == "processar_transcricao_factorial":
            texto = arguments.get("texto_transcricao")
            if not texto:
                return [TextContent(type="text", text="Erro: texto_transcricao é obrigatório")]
            
            resultado = processar_transcricao(texto)
            return [TextContent(
                type="text",
                text=json.dumps(resultado, ensure_ascii=False, indent=2, default=str)
            )]
        
        elif name == "processar_e_enviar_completo_factorial":
            texto = arguments.get("texto_transcricao")
            if not texto:
                return [TextContent(type="text", text="Erro: texto_transcricao é obrigatório")]
            
            # Processa transcrição
            resultado_processamento = processar_transcricao(texto)
            tarefas = resultado_processamento['tarefas']
            
            resultados = {
                'processamento': resultado_processamento,
                'email': None,
                'calendario': None
            }
            
            # Envia email
            if tarefas:
                resultados['email'] = enviar_email_tarefas(tarefas)
            
            # Cria eventos no calendário
            tarefas_com_deadline = [t for t in tarefas if t.get('deadline')]
            if tarefas_com_deadline:
                resultados['calendario'] = criar_eventos_calendario(tarefas_com_deadline)
            
            return [TextContent(
                type="text",
                text=json.dumps(resultados, ensure_ascii=False, indent=2, default=str)
            )]
        
        else:
            return [TextContent(type="text", text=f"Ferramenta desconhecida: {name}")]

    async def main():
        """Função principal do servidor MCP"""
        async with stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options()
            )


# ============================================================================
# INTERFACE DE LINHA DE COMANDO
# ============================================================================

if __name__ == "__main__":
    import sys
    
    # Se o MCP SDK está disponível e não há argumentos, roda como servidor MCP
    if MCP_AVAILABLE and len(sys.argv) == 1:
        print("🚀 Iniciando MCP Tarefas Factorial...")
        print("   Email: victor.gutierrez@factorial.co")
        print("   Calendário: victorgutierrez759@gmail.com")
        asyncio.run(main())
    
    # Caso contrário, roda como script normal
    else:
        if len(sys.argv) > 1:
            arquivo = ' '.join(sys.argv[1:])
            arquivo = arquivo.replace('/', '\\')
            
            print("=" * 60)
            print("📋 MCP TAREFAS FACTORIAL")
            print("=" * 60)
            print()
            print(f"📁 Processando: {arquivo}")
            print()
            
            try:
                with open(arquivo, 'r', encoding='utf-8') as f:
                    texto = f.read()
                
                print(f"✅ Arquivo lido com sucesso! ({len(texto)} caracteres)")
                print()
                
                resultado = processar_transcricao(texto)
                print(f"✅ {resultado['total']} tarefa(s) encontrada(s)")
                print(f"   ⏰ {resultado['com_deadline']} com deadline")
                print(f"   📝 {resultado['sem_deadline']} sem deadline")
                print()
                
                if resultado['tarefas']:
                    print("📧 Enviando email para victor.gutierrez@factorial.co...")
                    email_result = enviar_email_tarefas(resultado['tarefas'])
                    print(f"📧 {email_result.get('mensagem', email_result.get('erro'))}")
                    print()
                    
                    print("📅 Criando eventos no Google Calendar...")
                    calendario_result = criar_eventos_calendario(resultado['tarefas'])
                    print(f"📅 {calendario_result.get('mensagem', calendario_result.get('erro'))}")
                else:
                    print("ℹ️  Nenhuma tarefa encontrada na transcrição.")
                    
            except FileNotFoundError:
                print(f"❌ ERRO: Arquivo não encontrado!")
                print()
                print(f"   Caminho tentado: {arquivo}")
                print()
                print("💡 DICA: Coloque o caminho entre ASPAS se tiver espaços:")
                print('   python mcp_tarefas_factorial.py "C:\\caminho\\com espaços\\arquivo.txt"')
                sys.exit(1)
            except Exception as e:
                print(f"❌ ERRO: {e}")
                sys.exit(1)
        else:
            print("=" * 60)
            print("📋 MCP TAREFAS FACTORIAL")
            print("=" * 60)
            print()
            print("Configurado para:")
            print("  📧 Email: victor.gutierrez@factorial.co")
            print("  📅 Calendário: victorgutierrez759@gmail.com")
            print()
            print("Uso como script:")
            print('  python mcp_tarefas_factorial.py "caminho\\para\\transcricao.txt"')
            print()
            if MCP_AVAILABLE:
                print("Ou use como servidor MCP (sem argumentos):")
                print("  python mcp_tarefas_factorial.py")
                print()
                print("Configure no Cursor:")
                print('  "mcpServers": {')
                print('    "mcp-tarefas-factorial": {')
                print('      "command": "python",')
                print('      "args": ["C:/Users/victo/SEGLife/Novo Projeto/mcp_tarefas_factorial.py"]')
                print('    }')
                print('  }')
            print()

