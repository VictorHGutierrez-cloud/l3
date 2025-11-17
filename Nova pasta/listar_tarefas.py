#!/usr/bin/env python3
from mcp_tarefas_factorial import processar_transcricao
import json

with open('l3transcrição.txt','r',encoding='utf-8') as f:
    texto=f.read()

res = processar_transcricao(texto)

saida = {
    'total': res['total'],
    'tarefas': []
}
for t in res['tarefas']:
    saida['tarefas'].append({
        'texto': t.get('texto'),
        'responsavel': t.get('responsavel'),
        'tipo': t.get('tipo'),
        'deadline': t.get('deadline')
    })

print(json.dumps(saida, ensure_ascii=False, indent=2, default=str))

