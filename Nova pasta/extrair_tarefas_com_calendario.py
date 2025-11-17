#!/usr/bin/env python3
"""
Script COMPLETO para extrair tarefas de transcrições de reuniões
- Identifica tarefas e DEADLINES automaticamente
- Envia email formatado
- CRIA EVENTOS NO GOOGLE CALENDAR automaticamente

Uso: python extrair_tarefas_com_calendario.py <arquivo_transcricao.txt>
"""

import sys
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
import os

# ============================================================================
# CONFIGURAÇÕES - EDITE AQUI
# ============================================================================

MEU_EMAIL = "victor.gutierrez@factorial.co"
MEU_NOME = "Victor"

# Configurações de email (Google App Password)
SMTP_USER = "victor.gutierrez@factorial.co"
SMTP_PASS = "wglzlzyggeeivwmy"

# ============================================================================
# PADRÕES DE IDENTIFICAÇÃO
# ============================================================================

# Padrões de atribuição de tarefa
PADROES_ATRIBUICAO_DIRETA = [
    # Padrões diretos com nome
    r'victor[,:]?\s+(?:você\s+)?(?:pode|poderia|consegue)\s+(?:fazer|preparar|enviar|criar|desenvolver)',
    r'victor[,:]?\s+(?:você\s+)?(?:precisa|deve|tem que|vai ter que)\s+(?:fazer|preparar|enviar|criar)',
    r'(?:pede|peço|pediu)\s+(?:pro|para o?)\s+victor',
    r'victor\s+(?:fica|vai ficar)\s+responsável',
    r'victor[,:]?\s+(?:faz|faça|prepare|envie|crie|desenvolva)',
    
    # Padrões indiretos (contexto de conversa)
    r'(?:tem como|consegue|poderia|pode)\s+(?:você\s+)?(?:enviar|mandar|fazer|preparar|criar)',
    r'(?:você\s+)?(?:envia|manda|faz|prepara|cria).*(?:pra|para)\s+(?:mim|gente|nós)',
]

# Padrões de DEADLINE/PRAZO
PADROES_DEADLINE = [
    # Datas específicas
    r'(?:até|para|antes de?)\s+(?:dia\s+)?(\d{1,2})\s*(?:de\s+)?(\w+)?',  # até 15 de novembro
    r'(?:até|para)\s+(segunda|terça|quarta|quinta|sexta|sábado|domingo)(?:\s*-?\s*feira)?',
    r'(?:até|para)\s+(hoje|amanhã|depois de amanhã)',
    r'(?:prazo|deadline)[:\s]+([^\n.,;]+)',
    # Horários
    r'(?:às|as)\s+(\d{1,2})[h:]?(\d{2})?',  # às 10h ou às 10:30
    r'(?:hoje|amanhã)\s+às\s+(\d{1,2})[h:]?(\d{2})?',
    # Períodos relativos
    r'(?:em|dentro de)\s+(\d+)\s+(dia|dias|semana|semanas|mês|meses)',
    r'(?:final|fim)\s+(?:de|da)\s+(semana|mês)',
    r'(?:semana|mês)\s+que\s+vem',
]

# Padrões para IGNORAR
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

# ============================================================================
# CLASSE PRINCIPAL
# ============================================================================

class ExtratorTarefasCompleto:
    """Extrai tarefas E deadlines de transcrições"""
    
    def __init__(self, texto_reuniao: str):
        self.texto = texto_reuniao
        self.linhas = texto_reuniao.split('\n')
        self.tarefas = []
        self.data_reuniao = datetime.now()
    
    def extrair_deadline(self, texto: str, contexto_linhas: List[str]) -> Optional[Dict]:
        """
        Extrai deadline/prazo do texto e contexto
        Retorna dicionário com informações da data ou None
        """
        texto_completo = texto + " " + " ".join(contexto_linhas)
        texto_lower = texto_completo.lower()
        
        # Dias da semana
        dias_semana = {
            'segunda': 0, 'segunda-feira': 0,
            'terça': 1, 'terca': 1, 'terça-feira': 1, 'terca-feira': 1,
            'quarta': 2, 'quarta-feira': 2,
            'quinta': 3, 'quinta-feira': 3,
            'sexta': 4, 'sexta-feira': 4,
            'sábado': 5, 'sabado': 5,
            'domingo': 6
        }
        
        # Meses do ano
        meses = {
            'janeiro': 1, 'fevereiro': 2, 'março': 3, 'marco': 3,
            'abril': 4, 'maio': 5, 'junho': 6,
            'julho': 7, 'agosto': 8, 'setembro': 9,
            'outubro': 10, 'novembro': 11, 'dezembro': 12
        }
        
        # 1. Procura "hoje" ou "amanhã"
        if re.search(r'\bhoje\b', texto_lower):
            return {
                'data': self.data_reuniao.date(),
                'texto_original': 'hoje',
                'horario': None
            }
        
        if re.search(r'\bamanhã\b', texto_lower):
            return {
                'data': (self.data_reuniao + timedelta(days=1)).date(),
                'texto_original': 'amanhã',
                'horario': None
            }
        
        # 2. Procura dia da semana (próxima sexta, segunda, etc)
        for dia_nome, dia_num in dias_semana.items():
            if re.search(rf'\b{dia_nome}\b', texto_lower):
                # Calcula próximo dia da semana
                dias_ate = (dia_num - self.data_reuniao.weekday()) % 7
                if dias_ate == 0:
                    dias_ate = 7  # Próxima ocorrência
                data_deadline = self.data_reuniao + timedelta(days=dias_ate)
                return {
                    'data': data_deadline.date(),
                    'texto_original': dia_nome,
                    'horario': None
                }
        
        # 3. Procura "até dia X" ou "dia X de mês"
        match = re.search(r'(?:até|para|antes de?)\s+(?:dia\s+)?(\d{1,2})(?:\s+de\s+(\w+))?', texto_lower)
        if match:
            dia = int(match.group(1))
            mes_nome = match.group(2)
            
            if mes_nome and mes_nome in meses:
                mes = meses[mes_nome]
                ano = self.data_reuniao.year
                # Se o mês já passou este ano, considera ano que vem
                if mes < self.data_reuniao.month:
                    ano += 1
            else:
                # Sem mês especificado, assume mês atual ou próximo
                mes = self.data_reuniao.month
                ano = self.data_reuniao.year
                if dia < self.data_reuniao.day:
                    # Dia já passou, assume mês que vem
                    mes += 1
                    if mes > 12:
                        mes = 1
                        ano += 1
            
            try:
                data_deadline = datetime(ano, mes, dia).date()
                return {
                    'data': data_deadline,
                    'texto_original': match.group(0),
                    'horario': None
                }
            except ValueError:
                pass  # Data inválida
        
        # 4. Procura "em X dias/semanas"
        match = re.search(r'(?:em|dentro de)\s+(\d+)\s+(dia|dias|semana|semanas)', texto_lower)
        if match:
            quantidade = int(match.group(1))
            unidade = match.group(2)
            
            if 'semana' in unidade:
                dias = quantidade * 7
            else:
                dias = quantidade
            
            data_deadline = (self.data_reuniao + timedelta(days=dias)).date()
            return {
                'data': data_deadline,
                'texto_original': match.group(0),
                'horario': None
            }
        
        # 5. Procura "final da semana" ou "fim do mês"
        if re.search(r'(?:final|fim)\s+(?:de|da)\s+semana', texto_lower):
            # Próxima sexta-feira
            dias_ate_sexta = (4 - self.data_reuniao.weekday()) % 7
            if dias_ate_sexta == 0:
                dias_ate_sexta = 7
            data_deadline = (self.data_reuniao + timedelta(days=dias_ate_sexta)).date()
            return {
                'data': data_deadline,
                'texto_original': 'final da semana',
                'horario': None
            }
        
        # 6. Procura horários (às 10h, 15:30, etc)
        match = re.search(r'(?:às|as)\s+(\d{1,2})[h:]?(\d{2})?', texto_lower)
        if match:
            hora = int(match.group(1))
            minuto = int(match.group(2)) if match.group(2) else 0
            
            # Verifica se tem "hoje" ou "amanhã" junto
            if re.search(r'hoje.*' + re.escape(match.group(0)), texto_lower):
                data_base = self.data_reuniao.date()
            elif re.search(r'amanhã.*' + re.escape(match.group(0)), texto_lower):
                data_base = (self.data_reuniao + timedelta(days=1)).date()
            else:
                data_base = self.data_reuniao.date()
            
            return {
                'data': data_base,
                'texto_original': match.group(0),
                'horario': f'{hora:02d}:{minuto:02d}'
            }
        
        return None
    
    def e_atribuicao_direta(self, linha: str) -> bool:
        """Verifica se a linha contém uma atribuição DIRETA de tarefa"""
        linha_lower = linha.lower()
        
        # Checa se é do próprio Victor falando
        if re.search(r'^[^:]*victor[^:]*:', linha_lower):
            # É o Victor falando - verifica se é uma confirmação de tarefa
            confirmacoes = [
                # Confirmações diretas
                r'(?:ok|certo|sim|beleza)[,.]?\s+(?:vou|eu vou)\s+(?:fazer|preparar|enviar|criar|mandar)',
                r'(?:vou|eu vou)\s+(?:fazer|preparar|enviar|criar|desenvolver|mandar)',
                r'posso\s+fazer',
                r'faço\s+sim',
                
                # Promessas de entrega
                r'(?:te|vou)\s+(?:mandar|enviar|passar).*(?:hoje|amanhã|agora)',
                r'(?:mando|envio)\s+(?:ainda\s+)?(?:hoje|amanhã)',
            ]
            for padrao in confirmacoes:
                if re.search(padrao, linha_lower):
                    return True
            return False
        
        # Checa padrões de atribuição direta
        for padrao in PADROES_ATRIBUICAO_DIRETA:
            if re.search(padrao, linha_lower):
                # Verifica se não é um padrão a ignorar
                for padrao_ignorar in PADROES_IGNORAR:
                    if re.search(padrao_ignorar, linha_lower):
                        return False
                return True
        
        return False
    
    def obter_contexto(self, index: int, janela: int = 3) -> List[str]:
        """Obtém linhas de contexto ao redor da tarefa"""
        inicio = max(0, index - janela)
        fim = min(len(self.linhas), index + janela + 1)
        
        contexto = []
        for i in range(inicio, fim):
            if i != index and self.linhas[i].strip():
                linha_limpa = self.limpar_texto(self.linhas[i].strip())
                if linha_limpa and len(linha_limpa) > 10:
                    contexto.append(linha_limpa)
        
        return contexto
    
    def limpar_texto(self, texto: str) -> str:
        """Remove prefixos e limpa o texto"""
        # Remove timestamps
        texto = re.sub(r'^\d{1,2}:\d{2}(?::\d{2})?\s*[-–]\s*', '', texto).strip()
        
        # Remove nome do falante
        texto = re.sub(r'^[^:]+:\s*', '', texto).strip()
        
        # Remove marcadores
        texto = re.sub(r'^[\s\-\*\•\d\.\)]+', '', texto).strip()
        
        # Capitaliza primeira letra
        if texto:
            texto = texto[0].upper() + texto[1:]
        
        return texto
    
    def extrair_tarefas(self) -> List[Dict[str, any]]:
        """Extrai todas as tarefas atribuídas com deadlines"""
        tarefas_encontradas = []
        
        print("🔍 Analisando transcrição...")
        print(f"   Total de linhas: {len(self.linhas)}")
        print()
        
        for index, linha in enumerate(self.linhas):
            linha_original = linha.strip()
            
            if not linha_original or len(linha_original) < 15:
                continue
            
            # Verifica se é uma atribuição direta
            if self.e_atribuicao_direta(linha_original):
                # Limpa a tarefa
                tarefa_limpa = self.limpar_texto(linha_original)
                
                if tarefa_limpa and len(tarefa_limpa) > 10:
                    # Obtém contexto
                    contexto_linhas = self.obter_contexto(index)
                    contexto_texto = ' | '.join(contexto_linhas[:2]) if contexto_linhas else ''
                    
                    # Tenta extrair deadline
                    deadline_info = self.extrair_deadline(tarefa_limpa, contexto_linhas)
                    
                    tarefa = {
                        'texto': tarefa_limpa,
                        'linha_original': index + 1,
                        'contexto': contexto_texto,
                        'deadline': deadline_info
                    }
                    
                    tarefas_encontradas.append(tarefa)
                    
                    # Mostra no terminal
                    print(f"✅ Tarefa encontrada (linha {index + 1}):")
                    print(f"   {tarefa_limpa[:80]}...")
                    if deadline_info:
                        print(f"   ⏰ Deadline: {deadline_info['data']} ({deadline_info['texto_original']})")
                    print()
        
        # Remove duplicatas
        tarefas_unicas = []
        textos_vistos = set()
        
        for tarefa in tarefas_encontradas:
            texto_normalizado = re.sub(r'\s+', ' ', tarefa['texto'].lower().strip())
            
            if texto_normalizado not in textos_vistos:
                textos_vistos.add(texto_normalizado)
                tarefas_unicas.append(tarefa)
        
        self.tarefas = tarefas_unicas
        return tarefas_unicas


# ============================================================================
# GERAÇÃO DE EMAIL HTML
# ============================================================================

def gerar_email_html(tarefas: List[Dict], arquivo_origem: str) -> str:
    """Gera HTML formatado do email com as tarefas e deadlines"""
    
    data_hoje = datetime.now().strftime('%d/%m/%Y às %H:%M')
    
    # Separa tarefas com e sem deadline
    com_deadline = [t for t in tarefas if t.get('deadline')]
    sem_deadline = [t for t in tarefas if not t.get('deadline')]
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .container {{
                background-color: white;
                border-radius: 8px;
                padding: 30px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}
            h1 {{
                color: #2c3e50;
                border-bottom: 3px solid #3498db;
                padding-bottom: 10px;
            }}
            h2 {{
                color: #e74c3c;
                margin-top: 30px;
                border-left: 4px solid #e74c3c;
                padding-left: 10px;
            }}
            .metadata {{
                background-color: #ecf0f1;
                padding: 15px;
                border-radius: 5px;
                margin: 20px 0;
            }}
            .tarefa {{
                background-color: #fff;
                border-left: 4px solid #3498db;
                padding: 15px;
                margin: 15px 0;
                border-radius: 4px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }}
            .tarefa-urgente {{
                border-left-color: #e74c3c;
                background-color: #ffebee;
            }}
            .tarefa-numero {{
                background-color: #3498db;
                color: white;
                padding: 5px 10px;
                border-radius: 50%;
                font-weight: bold;
                display: inline-block;
                margin-right: 10px;
                min-width: 25px;
                text-align: center;
            }}
            .deadline {{
                background-color: #fff3cd;
                border: 1px solid #ffc107;
                padding: 10px;
                margin: 10px 0;
                border-radius: 4px;
                font-weight: bold;
            }}
            .deadline-urgente {{
                background-color: #ffebee;
                border-color: #e74c3c;
                color: #c62828;
            }}
            .contexto {{
                font-size: 13px;
                color: #7f8c8d;
                font-style: italic;
                margin-top: 8px;
                padding: 8px;
                background-color: #f8f9fa;
                border-radius: 3px;
            }}
            .footer {{
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #ecf0f1;
                text-align: center;
                color: #7f8c8d;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📋 Suas Tarefas da Reunião</h1>
            
            <div class="metadata">
                <strong>📁 Origem:</strong> {arquivo_origem}<br>
                <strong>📅 Processado em:</strong> {data_hoje}<br>
                <strong>✅ Total de tarefas:</strong> {len(tarefas)}<br>
                <strong>⏰ Com deadline:</strong> {len(com_deadline)} | <strong>📝 Sem deadline:</strong> {len(sem_deadline)}
            </div>
    """
    
    # Tarefas COM deadline (prioritárias)
    if com_deadline:
        html += '<h2>⏰ TAREFAS COM PRAZO (Prioridade!)</h2>'
        
        for i, tarefa in enumerate(com_deadline, 1):
            deadline = tarefa['deadline']
            data_deadline = deadline['data']
            dias_restantes = (data_deadline - datetime.now().date()).days
            
            # Define urgência
            if dias_restantes <= 0:
                urgencia_class = 'tarefa-urgente'
                urgencia_texto = f'🚨 VENCEU ou VENCE HOJE!'
            elif dias_restantes == 1:
                urgencia_class = 'tarefa-urgente'
                urgencia_texto = f'⚠️ AMANHÃ ({data_deadline.strftime("%d/%m/%Y")})'
            elif dias_restantes <= 3:
                urgencia_class = 'tarefa-urgente'
                urgencia_texto = f'⚠️ Em {dias_restantes} dias ({data_deadline.strftime("%d/%m/%Y")})'
            else:
                urgencia_class = 'tarefa'
                urgencia_texto = f'📅 {data_deadline.strftime("%d/%m/%Y")} (em {dias_restantes} dias)'
            
            horario_texto = f' às {deadline["horario"]}' if deadline.get('horario') else ''
            
            html += f"""
            <div class="{urgencia_class}">
                <div>
                    <span class="tarefa-numero">{i}</span>
                    <span style="font-size:16px; font-weight:bold;">{tarefa['texto']}</span>
                </div>
                <div class="deadline {'deadline-urgente' if 'urgente' in urgencia_class else ''}">
                    ⏰ {urgencia_texto}{horario_texto}
                </div>
            """
            
            if tarefa.get('contexto'):
                html += f'<div class="contexto">💬 Contexto: {tarefa["contexto"]}</div>'
            
            html += '</div>'
    
    # Tarefas SEM deadline
    if sem_deadline:
        html += '<h2>📝 Outras Tarefas</h2>'
        
        for i, tarefa in enumerate(sem_deadline, len(com_deadline) + 1):
            html += f"""
            <div class="tarefa">
                <div>
                    <span class="tarefa-numero">{i}</span>
                    <span style="font-size:16px; font-weight:bold;">{tarefa['texto']}</span>
                </div>
            """
            
            if tarefa.get('contexto'):
                html += f'<div class="contexto">💬 Contexto: {tarefa["contexto"]}</div>'
            
            html += '</div>'
    
    if not tarefas:
        html += """
            <div style="text-align:center; padding:40px; color:#7f8c8d;">
                <h3>🎉 Nenhuma tarefa identificada!</h3>
                <p>Ou as tarefas não foram claramente atribuídas na transcrição.</p>
            </div>
        """
    
    html += """
            <div class="footer">
                🤖 Email gerado automaticamente pelo Extrator de Tarefas<br>
                <small>⏰ Tarefas com deadline serão adicionadas ao Google Calendar</small>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html


# ============================================================================
# ENVIO DE EMAIL
# ============================================================================

def enviar_email(destinatario: str, assunto: str, corpo_html: str):
    """Envia email formatado"""
    
    if not SMTP_USER or not SMTP_PASS:
        print("\n⚠️  Email não configurado. Salvando HTML apenas.")
        return False
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = assunto
        msg['From'] = SMTP_USER
        msg['To'] = destinatario
        
        parte_html = MIMEText(corpo_html, 'html', 'utf-8')
        msg.attach(parte_html)
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        
        print(f"✅ Email enviado com sucesso para {destinatario}")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao enviar email: {e}")
        return False


# ============================================================================
# INTEGRAÇÃO COM GOOGLE CALENDAR
# ============================================================================

def criar_eventos_google_calendar(tarefas: List[Dict]):
    """
    Cria eventos no Google Calendar para tarefas com deadline
    
    NOTA: Requer configuração da API do Google Calendar
    """
    tarefas_com_deadline = [t for t in tarefas if t.get('deadline')]
    
    if not tarefas_com_deadline:
        print("\nℹ️  Nenhuma tarefa com deadline para adicionar ao calendário")
        return
    
    print("\n" + "="*60)
    print("📅 INTEGRAÇÃO COM GOOGLE CALENDAR")
    print("="*60)
    
    # Verifica se credenciais existem
    if not os.path.exists('credenciais_google.json'):
        print("\n⚠️  Integração com Google Calendar não configurada ainda.")
        print("\n📝 Para configurar:")
        print("1. Execute: python configurar_google_calendar.py")
        print("2. Siga as instruções para autorizar o acesso")
        print("\n💡 Por enquanto, as tarefas foram enviadas por email!")
        
        # Salva as tarefas para adicionar depois
        with open('tarefas_pendentes_calendario.json', 'w', encoding='utf-8') as f:
            json.dump(tarefas_com_deadline, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n💾 {len(tarefas_com_deadline)} tarefa(s) salva(s) em 'tarefas_pendentes_calendario.json'")
        print("   Você pode adicionar ao calendário depois de configurar.")
        return
    
    # Se chegou aqui, tenta usar a API
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        
        creds = Credentials.from_authorized_user_file('credenciais_google.json')
        service = build('calendar', 'v3', credentials=creds)
        
        eventos_criados = 0
        for tarefa in tarefas_com_deadline:
            deadline = tarefa['deadline']
            data_deadline = deadline['data']
            
            # Cria evento
            evento = {
                'summary': f'📋 {tarefa["texto"][:100]}',
                'description': f'Tarefa da reunião:\n\n{tarefa["texto"]}\n\nContexto: {tarefa.get("contexto", "N/A")}',
                'start': {
                    'date': data_deadline.isoformat(),
                },
                'end': {
                    'date': data_deadline.isoformat(),
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': 24 * 60},  # 1 dia antes
                        {'method': 'popup', 'minutes': 60},       # 1 hora antes
                    ],
                },
            }
            
            # Se tem horário, adiciona
            if deadline.get('horario'):
                hora, minuto = deadline['horario'].split(':')
                datetime_inicio = datetime.combine(data_deadline, datetime.min.time().replace(hour=int(hora), minute=int(minuto)))
                datetime_fim = datetime_inicio + timedelta(hours=1)
                
                evento['start'] = {'dateTime': datetime_inicio.isoformat(), 'timeZone': 'America/Sao_Paulo'}
                evento['end'] = {'dateTime': datetime_fim.isoformat(), 'timeZone': 'America/Sao_Paulo'}
            
            # Adiciona ao calendário
            evento_criado = service.events().insert(calendarId='primary', body=evento).execute()
            eventos_criados += 1
            
            print(f"✅ Evento criado: {tarefa['texto'][:60]}... ({data_deadline})")
        
        print(f"\n🎉 {eventos_criados} evento(s) adicionado(s) ao Google Calendar!")
        
    except ImportError:
        print("\n⚠️  Biblioteca do Google não instalada.")
        print("Execute: pip install google-auth google-auth-oauthlib google-api-python-client")
    except Exception as e:
        print(f"\n❌ Erro ao criar eventos: {e}")


# ============================================================================
# FUNÇÃO PRINCIPAL
# ============================================================================

def main():
    """Função principal"""
    
    print("=" * 60)
    print("📋 EXTRATOR DE TAREFAS COM GOOGLE CALENDAR")
    print("=" * 60)
    print()
    
    # Verifica argumentos
    if len(sys.argv) < 2:
        print("❌ Uso: python extrair_tarefas_com_calendario.py <arquivo.txt>")
        print()
        print("Exemplo:")
        print("  python extrair_tarefas_com_calendario.py reuniao.txt")
        sys.exit(1)
    
    arquivo_transcricao = sys.argv[1]
    
    # Lê o arquivo
    try:
        with open(arquivo_transcricao, 'r', encoding='utf-8') as f:
            texto_reuniao = f.read()
        print(f"✅ Arquivo lido: {arquivo_transcricao}")
        print(f"   Tamanho: {len(texto_reuniao)} caracteres")
        print()
    except FileNotFoundError:
        print(f"❌ Arquivo não encontrado: {arquivo_transcricao}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erro ao ler arquivo: {e}")
        sys.exit(1)
    
    # Extrai tarefas
    print("🔍 Analisando transcrição e extraindo tarefas...")
    print()
    extrator = ExtratorTarefasCompleto(texto_reuniao)
    tarefas = extrator.extrair_tarefas()
    
    print()
    print("="*60)
    print(f"✅ RESUMO: {len(tarefas)} tarefa(s) encontrada(s)")
    
    tarefas_com_deadline = [t for t in tarefas if t.get('deadline')]
    print(f"   ⏰ {len(tarefas_com_deadline)} com deadline")
    print(f"   📝 {len(tarefas) - len(tarefas_com_deadline)} sem deadline")
    print("="*60)
    print()
    
    # Mostra tarefas
    if tarefas:
        print("📝 TAREFAS IDENTIFICADAS:")
        print("-" * 60)
        for i, tarefa in enumerate(tarefas, 1):
            print(f"\n{i}. {tarefa['texto']}")
            if tarefa.get('deadline'):
                d = tarefa['deadline']
                print(f"   ⏰ Deadline: {d['data']} ({d['texto_original']})")
            if tarefa.get('contexto'):
                print(f"   💬 Contexto: {tarefa['contexto'][:80]}...")
        print()
    
    # Gera email
    print("📧 Gerando email...")
    assunto = f"📋 Suas Tarefas - {len(tarefas)} tarefa(s) - {datetime.now().strftime('%d/%m/%Y')}"
    corpo_html = gerar_email_html(tarefas, arquivo_transcricao)
    
    # Salva email em arquivo
    arquivo_email = f"tarefas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    with open(arquivo_email, 'w', encoding='utf-8') as f:
        f.write(corpo_html)
    print(f"✅ Email salvo em: {arquivo_email}")
    print()
    
    # Envia email
    print("📨 Enviando email...")
    enviado = enviar_email(MEU_EMAIL, assunto, corpo_html)
    print()
    
    # Integração com Google Calendar
    if tarefas_com_deadline:
        criar_eventos_google_calendar(tarefas)
    
    print()
    print("=" * 60)
    print("✅ PROCESSO CONCLUÍDO!")
    print("=" * 60)
    print()
    print("📧 Email enviado com suas tarefas")
    if tarefas_com_deadline:
        print(f"📅 {len(tarefas_com_deadline)} tarefa(s) com deadline identificada(s)")
        print("   💡 Execute 'configurar_google_calendar.py' para adicionar ao calendário")


if __name__ == "__main__":
    main()

