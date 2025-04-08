#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from flask import Flask

app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')

@app.route('/test')
def test():
    """Página de teste."""
    return "Servidor funcionando corretamente!"

# Verificar estrutura de arquivos estáticos
def check_static_files():
    static_path = os.path.join(os.path.dirname(__file__), 'static')
    js_path = os.path.join(static_path, 'js')
    css_path = os.path.join(static_path, 'css')
    
    print(f"Verificando diretório estático: {static_path}")
    print(f"Existe? {os.path.exists(static_path)}")
    
    print(f"\nVerificando diretório JS: {js_path}")
    print(f"Existe? {os.path.exists(js_path)}")
    if os.path.exists(js_path):
        js_files = os.listdir(js_path)
        print(f"Arquivos JS: {js_files}")
    
    print(f"\nVerificando diretório CSS: {css_path}")
    print(f"Existe? {os.path.exists(css_path)}")
    if os.path.exists(css_path):
        css_files = os.listdir(css_path)
        print(f"Arquivos CSS: {css_files}")

if __name__ == '__main__':
    print("Verificando arquivos estáticos...")
    check_static_files()
    
    print("\nIniciando servidor de teste...")
    app.run(debug=True, host='0.0.0.0', port=8001) 