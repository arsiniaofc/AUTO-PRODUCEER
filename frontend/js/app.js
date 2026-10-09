/**
 * Autonomous Music Producer - Frontend Vanilla JS
 */

const state = {
  activeTab: 'dashboard',
  isPlaying: false,
  bpm: 124,
  key: 'A minor',
  emergencyStop: false
};

const contentView = document.getElementById('contentView');
const navItems = document.querySelectorAll('.nav-item');

navItems.forEach((btn) => {
  btn.addEventListener('click', () => {
    navItems.forEach((b) => b.classList.remove('active'));
    btn.classList.add('active');
    state.activeTab = btn.getAttribute('data-tab');
    renderView();
  });
});

document.getElementById('btnPlay').addEventListener('click', () => {
  state.isPlaying = !state.isPlaying;
  document.getElementById('btnPlay').innerText = state.isPlaying ? 'Pausar' : 'Reproduzir';
});

document.getElementById('btnStop').addEventListener('click', () => {
  state.isPlaying = false;
  document.getElementById('btnPlay').innerText = 'Reproduzir';
  document.getElementById('positionCounter').innerText = 'Comp. 1 : 1';
});

function triggerEmergencyStop(source = 'Atalho de Teclado') {
  state.emergencyStop = true;
  state.isPlaying = false;
  const playBtn = document.getElementById('btnPlay');
  if (playBtn) playBtn.innerText = 'Reproduzir';

  const stopBtn = document.getElementById('btnEmergencyStop');
  if (stopBtn) {
    stopBtn.innerHTML = 'TRAVADO (Clique para Liberar) <kbd style="background: rgba(0,0,0,0.4); padding: 2px 5px; border-radius: 3px; font-family: monospace; font-size: 10px; margin-left: 6px;">Alt+S</kbd>';
    stopBtn.style.background = '#7f1d1d';
  }

  // Visual banner
  let banner = document.getElementById('shortcutAlertBanner');
  if (!banner) {
    banner = document.createElement('div');
    banner.id = 'shortcutAlertBanner';
    banner.style.cssText = 'background: #991b1b; color: #fff; padding: 10px 16px; font-size: 12px; font-weight: bold; border-bottom: 2px solid #ef4444; display: flex; justify-content: space-between; align-items: center;';
    document.querySelector('.main-viewport').insertBefore(banner, document.getElementById('contentView'));
  }
  banner.innerHTML = `<span>Auto Producer DESATIVADO imediatamente via ${source}! Todas as automações e reprodução foram interrompidas.</span> <button id="btnDismissAlert" style="background: #ef4444; color: #fff; border: none; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 11px;">Reativar</button>`;

  document.getElementById('btnDismissAlert')?.addEventListener('click', resetEmergencyStop);
}

function resetEmergencyStop() {
  state.emergencyStop = false;
  const stopBtn = document.getElementById('btnEmergencyStop');
  if (stopBtn) {
    stopBtn.innerHTML = 'DESATIVAR AUTO PRODUCER <kbd style="background: rgba(0,0,0,0.4); padding: 2px 5px; border-radius: 3px; font-family: monospace; font-size: 10px; margin-left: 6px;">ESC</kbd>';
    stopBtn.style.background = 'var(--accent-rose)';
  }
  const banner = document.getElementById('shortcutAlertBanner');
  if (banner) banner.remove();
}

document.getElementById('btnEmergencyStop').addEventListener('click', () => {
  if (state.emergencyStop) {
    resetEmergencyStop();
  } else {
    triggerEmergencyStop('Interface Manual');
  }
});

// Global Keyboard Shortcut: ESCAPE disables auto producer immediately
window.addEventListener('keydown', (e) => {
  const activeTag = (document.activeElement?.tagName || '').toLowerCase();
  const isInput = activeTag === 'input' || activeTag === 'textarea' || activeTag === 'select';

  if (e.key === 'Escape') {
    e.preventDefault();
    triggerEmergencyStop('Atalho [ESC]');
  }

  if (e.altKey && (e.key === 's' || e.key === 'S')) {
    e.preventDefault();
    if (state.emergencyStop) {
      resetEmergencyStop();
    } else {
      triggerEmergencyStop('Atalho [Alt+S]');
    }
  }

  if (e.code === 'Space' && !isInput) {
    e.preventDefault();
    state.isPlaying = !state.isPlaying;
    const playBtn = document.getElementById('btnPlay');
    if (playBtn) playBtn.innerText = state.isPlaying ? 'Pausar' : 'Reproduzir';
  }
});

function renderView() {
  if (state.activeTab === 'dashboard') {
    contentView.innerHTML = `
      <div class="grid-cards">
        <div class="card">
          <div class="card-title">Modelo Musical Ativo</div>
          <div class="card-value">Transformer v2.0</div>
          <div class="card-meta">Loss: <span style="color:var(--accent-emerald)">1.428</span> · CPU AMD Ryzen</div>
        </div>
        <div class="card">
          <div class="card-title">Biblioteca Analisada</div>
          <div class="card-value">12 arquivos</div>
          <div class="card-meta">MIDI (.mid) e Projetos (.flp)</div>
        </div>
        <div class="card">
          <div class="card-title">Conexão FL Studio</div>
          <div class="card-value" style="color:var(--accent-emerald)">Ponte Ativa</div>
          <div class="card-meta">Porta 9050 · Latência 2ms</div>
        </div>
        <div class="card">
          <div class="card-title">Hardware do Sistema</div>
          <div class="card-value">CPU 14% · RAM 2.4GB</div>
          <div class="card-meta">Otimizado para 8 GB RAM</div>
        </div>
      </div>

      <div class="card" style="margin-bottom: 24px;">
        <h3 style="font-size: 13px; font-weight: 700; margin-bottom: 12px; color: #fff;">
          Memória Cognitiva & Decisão Harmônica
        </h3>
        <p style="font-size: 12px; color: var(--text-muted); line-height: 1.6;">
          Tonalidade: <strong style="color: var(--accent-cyan)">Lá Menor (A Minor)</strong> ·
          Progressão: <strong style="color: var(--accent-amber)">i — VI — III — VII</strong> (Am → F → C → G)<br>
          Relação de Vozes: Baixo sustentando tônica na oitava 1; Acordes abertos na oitava 3-4; Melodia lírica pentatônica sem colisões de fase.
        </p>
      </div>
    `;
  } else if (state.activeTab === 'library') {
    contentView.innerHTML = `
      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>Nome do Arquivo</th>
              <th>Formato</th>
              <th>Tonalidade Estimada</th>
              <th>BPM</th>
              <th>Duração</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>cyberpunk_arpeggio.mid</td>
              <td>MIDI</td>
              <td>A Minor</td>
              <td>124</td>
              <td>32.5s</td>
              <td style="color: var(--accent-emerald)">Treinado</td>
            </tr>
            <tr>
              <td>trap_808_session.flp</td>
              <td>FLP</td>
              <td>D Minor</td>
              <td>140</td>
              <td>48.0s</td>
              <td style="color: var(--accent-emerald)">Treinado</td>
            </tr>
            <tr>
              <td>lofi_keys_progression.mid</td>
              <td>MIDI</td>
              <td>C Major</td>
              <td>85</td>
              <td>18.0s</td>
              <td style="color: var(--accent-amber)">Pendente</td>
            </tr>
          </tbody>
        </table>
      </div>
    `;
  } else if (state.activeTab === 'fl_studio') {
    contentView.innerHTML = `
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
        <div class="card">
          <div class="card-title" style="color: var(--accent-amber); font-weight: 700;">Camada A — MIDI Scripting Oficial</div>
          <p style="margin-top: 8px; font-size: 12px; color: var(--text-muted); line-height: 1.5;">
            Script em Python colocado na pasta Hardware do FL Studio para receber comandos diretos da API de transporte.
          </p>
        </div>
        <div class="card">
          <div class="card-title" style="color: var(--accent-amber); font-weight: 700;">Camada B — Ponte Socket Local (9050)</div>
          <p style="margin-top: 8px; font-size: 12px; color: var(--text-muted); line-height: 1.5;">
            Servidor IPC local transmitindo telemetria entre o produtor autônomo e a DAW com latência inferior a 3ms.
          </p>
        </div>
        <div class="card">
          <div class="card-title" style="color: var(--accent-amber); font-weight: 700;">Camada C — Guarda de Foco de Janela</div>
          <p style="margin-top: 8px; font-size: 12px; color: var(--text-muted); line-height: 1.5;">
            Verifica janela ativa do FL Studio antes de interagir. Nunca executa cliques cegos caso outra janela esteja aberta.
          </p>
        </div>
        <div class="card">
          <div class="card-title" style="color: var(--accent-amber); font-weight: 700;">Camada D — Verificação Pós-Ação</div>
          <p style="margin-top: 8px; font-size: 12px; color: var(--text-muted); line-height: 1.5;">
            Confirma a mudança de estado após cada comando enviado, interrompendo automações caso haja divergência.
          </p>
        </div>
      </div>
    `;
  } else {
    contentView.innerHTML = `
      <div class="card">
        <h3 style="font-size: 14px; font-weight: 700; color: #fff;">${state.activeTab.toUpperCase()}</h3>
        <p style="margin-top: 8px; font-size: 12px; color: var(--text-muted);">
          Módulo ativo e pronto para uso no Autonomous Music Producer.
        </p>
      </div>
    `;
  }
}

// Initial render
renderView();
