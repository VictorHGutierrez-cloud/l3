#!/usr/bin/env python3
"""
Script para configurar a integração com Google Calendar
Executa o processo de autenticação OAuth2 e salva as credenciais

USO: python configurar_google_calendar.py
"""

import os
import json

print("=" * 70)
print("📅 CONFIGURAÇÃO DO GOOGLE CALENDAR")
print("=" * 70)
print()

print("Este script vai configurar a integração com o Google Calendar.")
print("Você poderá adicionar tarefas automaticamente ao seu calendário!")
print()

# ==============================================================================
# PASSO 1: Verificar se as bibliotecas estão instaladas
# ==============================================================================

print("🔍 Verificando bibliotecas necessárias...")
print()

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from google.auth.transport.requests import Request
    print("✅ Bibliotecas do Google instaladas!")
except ImportError:
    print("❌ Bibliotecas do Google não encontradas.")
    print()
    print("📦 INSTALAÇÃO NECESSÁRIA:")
    print()
    print("Execute este comando no terminal:")
    print()
    print("    pip install google-auth google-auth-oauthlib google-api-python-client")
    print()
    print("Depois execute este script novamente.")
    input("\nPressione ENTER para sair...")
    exit(1)

print()

# ==============================================================================
# PASSO 2: Verificar se as credenciais do projeto Google existem
# ==============================================================================

print("🔍 Verificando credenciais do projeto Google...")
print()

CREDENTIALS_FILE = 'client_secret.json'  # Arquivo baixado do Google Cloud

if not os.path.exists(CREDENTIALS_FILE):
    print(f"❌ Arquivo '{CREDENTIALS_FILE}' não encontrado.")
    print()
    print("📝 COMO OBTER AS CREDENCIAIS:")
    print()
    print("1. Acesse: https://console.cloud.google.com/")
    print("2. Crie um novo projeto ou selecione um existente")
    print("3. No menu, vá em: APIs e Serviços > Biblioteca")
    print("4. Procure por 'Google Calendar API' e ATIVE")
    print("5. Vá em: APIs e Serviços > Credenciais")
    print("6. Clique em 'Criar credenciais' > 'ID do cliente OAuth'")
    print("7. Tipo de aplicativo: 'Aplicativo para computador'")
    print("8. Dê um nome (ex: 'Extrator de Tarefas')")
    print("9. Clique em 'CRIAR'")
    print(f"10. BAIXE o arquivo JSON e salve como '{CREDENTIALS_FILE}' nesta pasta")
    print()
    print(f"📁 Pasta atual: {os.getcwd()}")
    print()
    print("Depois execute este script novamente.")
    input("\nPressione ENTER para sair...")
    exit(1)

print(f"✅ Arquivo '{CREDENTIALS_FILE}' encontrado!")
print()

# ==============================================================================
# PASSO 3: Fazer a autenticação OAuth2
# ==============================================================================

print("🔐 Iniciando processo de autenticação...")
print()
print("📝 O que vai acontecer:")
print("1. Seu navegador vai abrir automaticamente")
print("2. Faça login com sua conta Google")
print("3. Autorize o acesso ao Google Calendar")
print("4. Volte aqui depois de autorizar")
print()

input("Pressione ENTER para continuar...")
print()

SCOPES = ['https://www.googleapis.com/auth/calendar']
TOKEN_FILE = 'credenciais_google.json'

creds = None

# Verifica se já existe um token salvo
if os.path.exists(TOKEN_FILE):
    print("ℹ️  Credenciais anteriores encontradas. Verificando validade...")
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

# Se não tem credenciais ou são inválidas, faz o fluxo OAuth
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        print("🔄 Renovando credenciais...")
        creds.refresh(Request())
    else:
        print("🌐 Abrindo navegador para autenticação...")
        print()
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
        print()
        print("✅ Autenticação concluída!")
    
    # Salva as credenciais para próximas execuções
    with open(TOKEN_FILE, 'w') as token:
        token.write(creds.to_json())
    print(f"💾 Credenciais salvas em: {TOKEN_FILE}")

print()

# ==============================================================================
# PASSO 4: Testar a conexão
# ==============================================================================

print("🧪 Testando conexão com Google Calendar...")
print()

try:
    service = build('calendar', 'v3', credentials=creds)
    
    # Lista calendários disponíveis
    print("📅 Seus calendários:")
    calendar_list = service.calendarList().list().execute()
    for calendar in calendar_list.get('items', []):
        print(f"   ✅ {calendar['summary']}")
    
    print()
    print("="*70)
    print("🎉 CONFIGURAÇÃO CONCLUÍDA COM SUCESSO!")
    print("="*70)
    print()
    print("✅ Você está pronto para usar a integração com Google Calendar!")
    print()
    print("📝 PRÓXIMOS PASSOS:")
    print()
    print("1. Execute o extrator de tarefas:")
    print("   python extrair_tarefas_com_calendario.py sua_reuniao.txt")
    print()
    print("2. As tarefas com deadline serão automaticamente:")
    print("   - Enviadas por email (formatadas e organizadas)")
    print("   - Adicionadas ao seu Google Calendar (com lembretes)")
    print()
    print("💡 DICA: Tarefas urgentes (próximas 3 dias) terão destaque especial!")
    print()
    
except Exception as e:
    print(f"❌ Erro ao testar conexão: {e}")
    print()
    print("Por favor, verifique:")
    print("- Se a Google Calendar API está ativada no projeto")
    print("- Se as credenciais estão corretas")
    print("- Se você autorizou o acesso ao calendário")

print()
input("Pressione ENTER para sair...")

