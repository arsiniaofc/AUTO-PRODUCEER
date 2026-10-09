# Integração com FL Studio (Modo Real-Time)

Para obter uma conexão em tempo real com o FL Studio, baseada no projeto `fl-studio-mcp`, siga estes passos manuais:

1. **Localize o repositório clonado:**
   Os scripts necessários estão na pasta `/fl-studio-mcp` no seu diretório do projeto.

2. **Instale o Script de Controlador MIDI:**
   - Copie o arquivo `/fl-studio-mcp/fl_controller/device_FLStudioMCP.py` para a pasta de hardware do FL Studio:
     - **Windows:** `%USERPROFILE%\Documents\Image-Line\FL Studio\Settings\Hardware\FLStudioMCP\`
     - (Crie as pastas se não existirem)

3. **Instale o Script do Piano Roll:**
   - Copie o arquivo `/fl-studio-mcp/scripts/ComposeWithLLM.pyscript` para a pasta de scripts do Piano Roll do FL Studio:
     - **Windows:** `%USERPROFILE%\Documents\Image-Line\FL Studio\Settings\Piano roll scripts\`

4. **Configure o FL Studio:**
   - Abra o FL Studio.
   - Vá em **Options > MIDI Settings**.
   - Em **Input**, selecione a porta MIDI virtual (se estiver usando loopMIDI, selecione-a).
   - Defina o **Controller type** como **FLStudioMCP**.
   - Habilite a porta.

5. **Uso:**
   - No Piano Roll, vá em **Tools > Scripting > ComposeWithLLM** para ativar o script.
