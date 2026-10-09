# Autonomous Music Producer — IA Musical Local com Controle do FL Studio

Aplicativo local desktop de produção musical assistida por inteligência artificial, capaz de aprender com arquivos MIDI e projetos FL Studio (.flp) fornecidos pelo usuário, treinar modelos neurais localmente e produzir composições multitrack de forma autônoma.

---

## 1. Principais Recursos e Diferenciais

- **100% Local e Privativo:** Não depende de APIs externas, chaves de acesso ou nuvem. O modelo musical roda diretamente no seu computador.
- **Otimizado para AMD Ryzen 5 & 8 GB de RAM:** Modelos compactos com batch size e sequências ajustáveis, priorizando execução rápida na CPU.
- **Leitura & Análise Harmônica Real:** Algoritmo Krumhansl-Schmuckler para identificação de tonalidade, extração de progressões de acordes em graus romanos, detecção de conflitos de registro e preenchimento de lacunas de arranjo.
- **Leitor de Projetos FL Studio (.flp) e MIDI (.mid):** Extração de canais, instrumentos, padrões, tempo e automações.
- **Aprendizado Contínuo com Replay Buffer:** Treine com novas músicas sem esquecimento catastrófico das anteriores, com versionamento e reversão de checkpoints.
- **Integração em 4 Camadas com o FL Studio:**
  - **Camada A:** Integração Estruturada via script oficial em Python da API MIDI do FL Studio (`device_AutonomousProducer.py`).
  - **Camada B:** Ponte Local Socket IPC (127.0.0.1:9050) para controle em tempo real.
  - **Camada C:** Automação segura com validação de foco de janela (sem cliques cegos).
  - **Camada D:** Verificação pós-ação com botão de parada de emergência imediata.
- **Web Audio Engine Embutido:** Sintetizador polifônico (Bateria, Baixo, Teclas e Melodia) e visualizador de Piano Roll interativo.
- **Atalhos Rápidos Globais de Segurança:**
  - `ESC`: Desativa imediatamente o Auto Producer e interrompe qualquer automação da DAW ou síntese.
  - `Alt + S`: Alterna a trava de segurança / reativa o Auto Producer.
  - `Espaço`: Reproduzir / Pausar áudio na timeline.
  - MIDI CC `#30`: Comando nativo no script do FL Studio para parada de emergência e desfazer (Undo).

---

## 2. Como Executar no seu Computador (Windows 10/11)

### Opção 1: Inicialização Rápida em 1 Clique (Recomendado)

1. Para a primeira execução, dê um duplo clique em `setup_windows.bat` para instalar as dependências necessárias.
2. Dê um duplo clique em `iniciar_windows.bat` (ou execute `python iniciar.py`).
3. O servidor local iniciará e a interface abrirá automaticamente no navegador em:
   `http://127.0.0.1:8000`

### Opção 2: Linha de Comando (Terminal / CMD / PowerShell)

```bash
# 1. Instalar dependências (apenas na primeira vez):
python -m pip install -r requirements.txt

# 2. Iniciar o programa:
python iniciar.py
```

---

## 3. Estrutura do Projeto

```
├── train/                   # PASTA DE TREINO: Coloque seus arquivos .mid e .flp aqui!
├── iniciar.py               # Ponto de entrada com diagnóstico e auto-abertura de navegador
├── server.py                # Servidor local HTTP e API REST
├── requirements.txt         # Dependências Python (PyTorch CPU, PyFLP, Mido, SQLite, etc.)
├── setup_windows.bat        # Instalador automático para Windows
├── iniciar_windows.bat      # Atalho de execução para Windows
├── backend/
│   ├── storage/db.py        # Persistência SQLite (metadados, modelos, logs)
│   ├── music_theory/        # Análise harmônica Krumhansl-Schmuckler e acordes
│   ├── midi/                # Parser binário SMF e Tokenizador musical REMI
│   ├── flp/                 # Parser binário e PyFLP para arquivos .flp
│   ├── model/               # Transformer Autoregressivo para CPU
│   ├── training/            # Treinamento contínuo com Replay Buffer
│   ├── generation/          # Geração de músicas completas, stems e variações
│   ├── fl_studio/           # Ponte IPC, automação segura e script oficial FL Studio
│   └── memory/              # Memória de cognição musical e estado da DAW
├── frontend/                # Interface nativa HTML5, CSS3 e JavaScript
├── data/                    # Banco de dados SQLite e músicas geradas (.mid)
├── models/                  # Checkpoints dos modelos treinados
└── tests/                   # Bateria de testes automatizados
```

---

## 4. Como Treinar a IA com suas Próprias Músicas (Pasta `train/`)

1. Abra a pasta `train/` na raiz do projeto.
2. Copie e cole seus arquivos `.mid` (MIDI) ou `.flp` (projetos FL Studio) lá dentro.
3. Inicie o aplicativo executando `python iniciar.py` (ou `iniciar_windows.bat`).
4. Na interface, vá na aba **Treinamento da IA**.
5. Clique no botão verde: **"Treinar Modelo com Pasta 'train/'"**.
6. A IA lerá seus arquivos, extrairá a tonalidade, acordes, ritmo e andamento, e treinará o modelo localmente na sua CPU!

---

## 5. Testes Automatizados

Para rodar a verificação de integridade dos módulos Python:

```bash
python3 -m unittest discover tests
```
