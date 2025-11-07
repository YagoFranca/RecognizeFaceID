"""
Script para diagnosticar e corrigir problemas com a instalação do dlib
"""

import sys
import subprocess
import platform

def run_command(command, description):
    """Executa um comando e mostra o resultado"""
    print(f"\n{'='*60}")
    print(f"🔧 {description}")
    print(f"{'='*60}")
    print(f"Executando: {command}")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("⚠️ Avisos/Erros:")
            print(result.stderr)
        
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("❌ Timeout: O comando demorou muito para executar")
        return False
    except Exception as e:
        print(f"❌ Erro ao executar comando: {e}")
        return False

def check_python_version():
    """Verifica a versão do Python"""
    print(f"\n🐍 Python Version: {sys.version}")
    print(f"📍 Python Path: {sys.executable}")
    
    version_info = sys.version_info
    if version_info.major == 3 and 7 <= version_info.minor <= 11:
        print("✅ Versão do Python compatível")
        return True
    else:
        print("⚠️ Versão do Python pode ter problemas de compatibilidade")
        print("   Recomendado: Python 3.8 - 3.11")
        return False

def check_architecture():
    """Verifica a arquitetura do sistema"""
    arch = platform.architecture()
    machine = platform.machine()
    
    print(f"\n💻 Arquitetura: {arch[0]}")
    print(f"🖥️ Máquina: {machine}")
    
    if arch[0] == "64bit":
        print("✅ Sistema 64-bit detectado")
        return True
    else:
        print("⚠️ Sistema 32-bit pode ter problemas com dlib")
        return False

def diagnose_dlib():
    """Diagnostica problemas com o dlib"""
    print(f"\n{'='*60}")
    print("🔍 DIAGNÓSTICO DO DLIB")
    print(f"{'='*60}")
    
    try:
        import dlib
        print(f"✅ dlib importado com sucesso")
        print(f"   Versão: {dlib.__version__ if hasattr(dlib, '__version__') else 'desconhecida'}")
        
        # Tentar usar a função problemática
        try:
            detector = dlib.get_frontal_face_detector()
            print("✅ get_frontal_face_detector() funcionando!")
            return True
        except AttributeError as e:
            print(f"❌ Erro ao chamar get_frontal_face_detector(): {e}")
            print("   O dlib está instalado, mas não está funcionando corretamente")
            return False
            
    except ImportError as e:
        print(f"❌ dlib não está instalado ou não pode ser importado: {e}")
        return False

def fix_dlib_windows():
    """Tenta corrigir a instalação do dlib no Windows"""
    print(f"\n{'='*60}")
    print("🔧 CORREÇÃO DO DLIB NO WINDOWS")
    print(f"{'='*60}")
    
    steps = [
        {
            "description": "Desinstalando dlib atual",
            "command": f'"{sys.executable}" -m pip uninstall -y dlib'
        },
        {
            "description": "Atualizando pip, setuptools e wheel",
            "command": f'"{sys.executable}" -m pip install --upgrade pip setuptools wheel'
        },
        {
            "description": "Instalando CMake (necessário para compilar dlib)",
            "command": f'"{sys.executable}" -m pip install cmake'
        },
        {
            "description": "Instalando dlib pré-compilado (pode levar alguns minutos)",
            "command": f'"{sys.executable}" -m pip install dlib --no-cache-dir'
        }
    ]
    
    for step in steps:
        success = run_command(step["command"], step["description"])
        if not success:
            print(f"\n⚠️ Aviso: Etapa pode ter falhado, mas continuando...")
    
    # Verificar se a correção funcionou
    print(f"\n{'='*60}")
    print("🧪 VERIFICANDO CORREÇÃO")
    print(f"{'='*60}")
    
    return diagnose_dlib()

def alternative_install_method():
    """Método alternativo usando arquivo wheel pré-compilado"""
    print(f"\n{'='*60}")
    print("🔧 MÉTODO ALTERNATIVO: INSTALAÇÃO VIA WHEEL PRÉ-COMPILADO")
    print(f"{'='*60}")
    
    print("""
📦 Se o método padrão falhar, você pode tentar instalar um arquivo .whl pré-compilado:

1. Acesse: https://github.com/z-mahmud22/Dlib_Windows_Python3.x
2. Baixe o arquivo .whl apropriado para sua versão do Python:
   - Python 3.8 (64-bit): dlib-19.24.1-cp38-cp38-win_amd64.whl
   - Python 3.9 (64-bit): dlib-19.24.1-cp39-cp39-win_amd64.whl
   - Python 3.10 (64-bit): dlib-19.24.1-cp310-cp310-win_amd64.whl
   - Python 3.11 (64-bit): dlib-19.24.1-cp311-cp311-win_amd64.whl

3. Abra o terminal na pasta onde baixou o arquivo e execute:
   python -m pip install nome_do_arquivo.whl

Exemplo:
   python -m pip install dlib-19.24.1-cp310-cp310-win_amd64.whl
    """)
    
    print("\nAlternativamente, você pode instalar usando o link direto:")
    
    version_info = sys.version_info
    if version_info.minor == 8:
        wheel_url = "https://github.com/z-mahmud22/Dlib_Windows_Python3.x/raw/main/dlib-19.24.1-cp38-cp38-win_amd64.whl"
    elif version_info.minor == 9:
        wheel_url = "https://github.com/z-mahmud22/Dlib_Windows_Python3.x/raw/main/dlib-19.24.1-cp39-cp39-win_amd64.whl"
    elif version_info.minor == 10:
        wheel_url = "https://github.com/z-mahmud22/Dlib_Windows_Python3.x/raw/main/dlib-19.24.1-cp310-cp310-win_amd64.whl"
    elif version_info.minor == 11:
        wheel_url = "https://github.com/z-mahmud22/Dlib_Windows_Python3.x/raw/main/dlib-19.24.1-cp311-cp311-win_amd64.whl"
    else:
        print(f"⚠️ Não há wheel pré-compilado disponível para Python 3.{version_info.minor}")
        return False
    
    print(f"\nComando para sua versão do Python ({sys.version_info.major}.{sys.version_info.minor}):")
    command = f'"{sys.executable}" -m pip install {wheel_url}'
    print(f"  {command}")
    
    response = input("\n❓ Deseja tentar instalar agora? (s/n): ").lower()
    if response == 's':
        return run_command(command, "Instalando dlib via wheel pré-compilado")
    
    return False

def main():
    """Função principal"""
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║   🔧 DIAGNÓSTICO E CORREÇÃO DO DLIB NO WINDOWS          ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    # Verificações iniciais
    check_python_version()
    check_architecture()
    
    # Diagnosticar problema atual
    if diagnose_dlib():
        print("\n✅ O dlib está funcionando corretamente!")
        print("   Se você ainda está tendo problemas, eles podem ser de outra natureza.")
        return
    
    # Tentar corrigir
    print("\n❓ Deseja tentar corrigir automaticamente? (s/n): ", end="")
    response = input().lower()
    
    if response == 's':
        if fix_dlib_windows():
            print("\n✅ SUCESSO! O dlib foi instalado e está funcionando!")
            print("   Você pode agora executar seu script de reconhecimento facial.")
        else:
            print("\n⚠️ A correção automática não funcionou completamente.")
            print("   Vamos tentar o método alternativo...")
            alternative_install_method()
    else:
        print("\n📋 RESUMO DO PROBLEMA:")
        print("   O dlib não está funcionando corretamente.")
        print("   Você pode tentar:")
        print("   1. Executar este script novamente e aceitar a correção automática")
        print("   2. Instalar manualmente usando o método wheel (mostrado acima)")
        alternative_install_method()
    
    print(f"\n{'='*60}")
    print("🏁 DIAGNÓSTICO FINALIZADO")
    print(f"{'='*60}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Processo interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()