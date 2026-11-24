/* ==========================================================================
   MINERACORE - INTERFACE DE DIMENSIONAMENTO DE CARGA E TRANSPORTE
   Responsabilidade exclusiva:
- Capturar interações da interface (cliques, inputs, selects)
- Enviar requisições JSON com token CSRF para as rotas Python (/api/*)
- Renderizar resultados e gerenciar cache local de até 2 cenários
   ========================================================================== */
'use strict';

// =========================================================================
// 1. DADOS INICIAIS DO CONTRATO E CHAVES DE CACHE (LOCALSTORAGE)
// =========================================================================
const PLANO = JSON.parse(document.getElementById('plano-data')?.textContent || '{}');
const NOME_CONTRATO = PLANO.contrato || 'geral';

const CHAVE_CACHE = `mineracore_cenarios_${NOME_CONTRATO.replace(/\s+/g, '_')}`;
const CHAVE_ESCOLHIDO = `mineracore_cenario_escolhido_${NOME_CONTRATO.replace(/\s+/g, '_')}`;
const CHAVE_ESCOLHIDO_GLOBAL = 'mineracore_cenario_escolhido_ativo';

// Mapeia os IDs dos inputs HTML para as chaves esperadas pelo backend Python
const MAPA_CAMPOS_FORM = {
    perfil_piso: 'perfilPiso',
    margem_falha: 'margemFalhaPct',
    modelo_escavadeira: 'modEscav',
    cacamba_m3: 'cacamba',
    fator_enchimento_pct: 'fatorEnchimentoPct',
    ciclo_escav_seg: 'cicloEscav',
    efic_escav: 'eficEscavPct',
    modelo_caminhao: 'modCam',
    carga_caminhao_t: 'cargaCaminhao',
    efic_transp: 'eficTranspPct'
};

// Guarda o último resultado retornado pelo Python para permitir salvar no comparativo
let ultimaSimulacao = null;

// =========================================================================
// 2. FUNÇÕES AUXILIARES DE DOM, FORMATAÇÃO E CABEÇALHO CSRF
// =========================================================================
const el = (id) => document.getElementById(id);
const str = (id) => (el(id)?.value || '').trim();
const fmt = (v) => Number(v || 0).toLocaleString('pt-BR', { maximumFractionDigits: 0 });

// Lê o token CSRF da meta tag no <head> para autorizar requisições POST no Flask
function obterHeadersJson() {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content
        || document.querySelector('input[name="csrf_token"]')?.value
        || '';

    return {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
    };
}

// Exibe ou oculta blocos da tela de forma padronizada
function alternarVisibilidade(elemento, visivel) {
    if (!elemento) return;
    elemento.classList.toggle('ocultar', !visivel);
    elemento.style.display = visivel ? 'block' : 'none';
}

// Coleta os valores brutos digitados no formulário para enviar ao Python
function lerInputsFormulario() {
    return {
        perfilPiso: str('perfil_piso'),
        margemFalhaPct: str('margem_falha'),
        modEscav: str('modelo_escavadeira'),
        cacamba: str('cacamba_m3'),
        fatorEnchimentoPct: str('fator_enchimento_pct'),
        cicloEscav: str('ciclo_escav_seg'),
        eficEscavPct: str('efic_escav'),
        modCam: str('modelo_caminhao'),
        cargaCaminhao: str('carga_caminhao_t'),
        eficTranspPct: str('efic_transp')
    };
}

// =========================================================================
// 3. COMUNICAÇÃO COM AS APIS PYTHON (SUGESTÃO, PREVIEW E SIMULAÇÃO)
// =========================================================================

// Atualiza o fator de enchimento padrão conforme o perfil geotécnico escolhido
async function atualizarFatorEnchimentoPiso() {
    const resp = await fetch('/api/sugerir_frota', {
        method: 'POST',
        headers: obterHeadersJson(),
        body: JSON.stringify({ acao: 'piso', inputs: lerInputsFormulario() })
    });
    if (!resp.ok) return;
    const data = await resp.json();

    if (data.fator_enchimento_pct !== undefined && el('fator_enchimento_pct')) {
        el('fator_enchimento_pct').value = data.fator_enchimento_pct;
    }
    await atualizarPreviewEscavadeira();
}

// Atualiza o indicador rápido de massa/passe e produtividade unitária da escavadeira
async function atualizarPreviewEscavadeira() {
    const preview = el('preview-escavadeira');
    const badge = el('badge-classe-escav');
    if (!preview || !badge) return;

    const resp = await fetch('/api/sugerir_frota', {
        method: 'POST',
        headers: obterHeadersJson(),
        body: JSON.stringify({ acao: 'preview', inputs: lerInputsFormulario() })
    });
    if (!resp.ok) return;
    const p = await resp.json();

    badge.textContent = p.classe_porte || 'Classe Carga';
    preview.innerHTML = `
        <span>Massa/Passe: <strong>${p.massa_passe_texto || '-- t'}</strong></span>
        <span>Prod. Unitária: <strong>${p.prod_unit_texto || '-- t/h'}</strong></span>
    `;
}

// Solicita ao Python uma configuração compatível de escavadeira + caminhão e simula
async function sugerirFrotaCompativel() {
    const resp = await fetch('/api/sugerir_frota', {
        method: 'POST',
        headers: obterHeadersJson(),
        body: JSON.stringify({ acao: 'preset', inputs: lerInputsFormulario() })
    });
    if (!resp.ok) {
        alert(`Erro ao sugerir frota (HTTP ${resp.status}).`);
        return;
    }
    const sug = await resp.json();

    // Preenche os campos da tela com os valores sugeridos pelo servidor
    if (sug.fator_enchimento_pct !== undefined && el('fator_enchimento_pct')) el('fator_enchimento_pct').value = sug.fator_enchimento_pct;
    if (sug.modEscav !== undefined && el('modelo_escavadeira')) el('modelo_escavadeira').value = sug.modEscav;
    if (sug.cacamba !== undefined && el('cacamba_m3')) el('cacamba_m3').value = sug.cacamba;
    if (sug.cicloEscav !== undefined && el('ciclo_escav_seg')) el('ciclo_escav_seg').value = sug.cicloEscav;
    if (sug.eficEscavPct !== undefined && el('efic_escav')) el('efic_escav').value = sug.eficEscavPct;
    if (sug.modCam !== undefined && el('modelo_caminhao')) el('modelo_caminhao').value = sug.modCam;
    if (sug.cargaCaminhao !== undefined && el('carga_caminhao_t')) el('carga_caminhao_t').value = sug.cargaCaminhao;
    if (sug.eficTranspPct !== undefined && el('efic_transp')) el('efic_transp').value = sug.eficTranspPct;
    if (sug.margemFalhaPct !== undefined && el('margem_falha') && !el('margem_falha').value) el('margem_falha').value = sug.margemFalhaPct;

    await atualizarPreviewEscavadeira();
    await simularFrota(sug.criterio || '');
}

// Envia os parâmetros ao Python (/api/simular_frota) e desenha o resultado completo
async function simularFrota(criterioSugestao = '') {
    const resp = await fetch('/api/simular_frota', {
        method: 'POST',
        headers: obterHeadersJson(),
        body: JSON.stringify({ inputs: lerInputsFormulario(), criterio: criterioSugestao })
    });
    if (!resp.ok) {
        alert(`Erro ao simular frota (HTTP ${resp.status}).`);
        return;
    }
    const data = await resp.json();

    if (data.erro) {
        alert(data.erro);
        return;
    }

    const res = data.simulacao;
    ultimaSimulacao = res;

    renderizarMemorialSugestao(res);
    renderizarCardsResultado(res);
    alternarVisibilidade(el('bloco-resultado-frota'), true);
}

// =========================================================================
// 4. RENDERIZAÇÃO DOS CARDS E DIAGNÓSTICOS NA TELA PRINCIPAL
// =========================================================================
function renderizarMemorialSugestao(res) {
    const memorial = el('memorial-sugestao');
    if (!memorial) return;

    if (!res?.criterio) {
        alternarVisibilidade(memorial, false);
        return;
    }

    alternarVisibilidade(memorial, true);
    if (el('memorial-sugestao-grid')) {
        el('memorial-sugestao-grid').innerHTML = `
            <div class="memorial-item"><small>Critério</small><strong>${res.criterio}</strong></div>
            <div class="memorial-item"><small>Massa/Passe</small><strong>${res.toneladasPasse} t</strong></div>
            <div class="memorial-item"><small>Carregamento</small><strong>${res.passadas} passes = ${res.cargaReal} t (${res.fatorCarregamentoPct}%)</strong></div>
            <div class="memorial-item"><small>Tempo Carga</small><strong>${res.tempoCargaMin} min</strong></div>
        `;
    }
}

function renderizarCardsResultado(res) {
    if (el('resumo-km-terreno')) {
        el('resumo-km-terreno').innerHTML = `
            <strong>Condição:</strong> ${res.nomePiso} (+${res.margemFalhaPct}% reserva) |
            <strong>Rodagem:</strong> ${res.kmTotalHora} km/h (${fmt(res.kmTotalAno)} km/ano)
        `;
    }

    if (el('cards-resultado-frota')) {
        el('cards-resultado-frota').innerHTML = `
            <div class="card-stat">
                <div class="title">Escavadeiras (Carga)</div>
                <div class="value">${res.qtdEscavadeiras}</div>
                <div class="unit">Nominal: ${res.escavNominal} | ${res.prodEscavadeiraTH} t/h</div>
            </div>
            <div class="card-stat">
                <div class="title">Caminhões (Transporte)</div>
                <div class="value">${res.qtdCaminhoes}</div>
                <div class="unit">Nominal: ${res.camNominal} | ${res.prodPorCaminhaoTH} t/h (${res.passadas} passes)</div>
            </div>
        `;
    }

    if (el('indicadores-acoplamento')) {
        el('indicadores-acoplamento').innerHTML = `
            <div class="acoplamento-grid">
                <div><span class="label-indicador">Match Factor:</span><strong class="valor-indicador ${res.classeMF || ''}">${res.matchFactor} — ${res.statusMF || ''}</strong></div>
                <div><span class="label-indicador">Relação Frota:</span><strong class="valor-indicador">${res.relacaoFrotaTexto || ''}</strong></div>
                <div><span class="label-indicador">Capacidade Instalada:</span><strong class="valor-indicador destaque-ritmo">${res.capCargaTH} t/h (Carga) | ${res.capTranspTH} t/h (Transp.)</strong></div>
            </div>
        `;
    }

    if (el('diagnostico-engenharia')) {
        el('diagnostico-engenharia').innerHTML = `
            <div class="diagnostico-box">
                <div class="diagnostico-titulo">Diagnóstico Técnico de Engenharia</div>
                <ul class="diagnostico-lista">${(res.alertas || []).map((a) => `<li>${a}</li>`).join('')}</ul>
            </div>
        `;
    }
}

// =========================================================================
// 5. GERENCIAMENTO DE CACHE LOCAL (ATÉ 2 OPÇÕES PARA CONFRONTO)
// =========================================================================
function removerTodoCacheContrato() {
    localStorage.removeItem(CHAVE_CACHE);
    localStorage.removeItem(CHAVE_ESCOLHIDO);
    localStorage.removeItem(CHAVE_ESCOLHIDO_GLOBAL);
}

function lerCache() {
    try {
        const dados = JSON.parse(localStorage.getItem(CHAVE_CACHE));
        return Array.isArray(dados) ? dados : [];
    } catch {
        return [];
    }
}

function gravarCache(lista) {
    localStorage.setItem(CHAVE_CACHE, JSON.stringify(lista));
}

function salvarCenarioCache() {
    if (!ultimaSimulacao) {
        alert('Simule a frota primeiro antes de gravar.');
        return;
    }

    const cenarios = lerCache();
    if (cenarios.length >= 2) {
        alert('Limite de 2 opções atingido. Exclua uma antes de gravar outra.');
        return;
    }

    const nome = str('nome_cenario') || `Opção ${cenarios.length + 1}`;
    cenarios.push({ id: Date.now(), nome, ...ultimaSimulacao });
    gravarCache(cenarios);

    if (el('nome_cenario')) el('nome_cenario').value = '';
    renderizarTabelaComparativa();
    renderizarPaginaComparativaDupla();

    const feedback = el('feedback-cenario');
    if (feedback) feedback.textContent = `✅ "${nome}" gravada (${cenarios.length}/2).`;
}

// Recarrega uma opção salva de volta nos inputs e executa nova simulação
async function carregarCenarioNoFormulario(id) {
    const cenario = lerCache().find((item) => item.id === id);
    if (!cenario || !cenario.inputs) return;

    Object.entries(MAPA_CAMPOS_FORM).forEach(([campoId, chaveInput]) => {
        if (el(campoId) && cenario.inputs[chaveInput] !== undefined) {
            el(campoId).value = cenario.inputs[chaveInput];
        }
    });

    await simularFrota(cenario.criterio || '');
}

function removerCenarioCache(id) {
    gravarCache(lerCache().filter((c) => c.id !== id));
    renderizarTabelaComparativa();
    renderizarPaginaComparativaDupla();
}

function limparCenariosCache() {
    if (confirm('Deseja apagar as opções gravadas neste contrato?')) {
        removerTodoCacheContrato();
        renderizarTabelaComparativa();
        renderizarPaginaComparativaDupla();
    }
}

// Grava a opção escolhida no localStorage e abre o módulo de Infraestrutura
function abrirDimensionamentoInfra(cenarioId) {
    const cenario = lerCache().find((item) => item.id === cenarioId);
    const urlInfra = el('container-comparativo-duplo')?.dataset.urlInfra;
    if (!cenario || !urlInfra) {
        alert('Erro ao localizar cenário ou URL de infraestrutura.');
        return;
    }

    const payload = JSON.stringify(cenario);
    localStorage.setItem(CHAVE_ESCOLHIDO, payload);
    localStorage.setItem(CHAVE_ESCOLHIDO_GLOBAL, payload);
    window.open(urlInfra, '_blank');
}

// =========================================================================
// 6. RENDERIZAÇÃO DA LISTA RESUMIDA E DA PÁGINA COMPARATIVA (OPÇÃO 1 VS 2)
// =========================================================================
function renderizarTabelaComparativa() {
    const cenarios = lerCache();
    const bloco = el('bloco-comparativo-cenarios');
    const lista = el('lista-mini-cenarios');
    if (!bloco || !lista) return;

    if (!cenarios.length) {
        alternarVisibilidade(bloco, false);
        return;
    }

    alternarVisibilidade(bloco, true);

    if (el('resumo-cenarios-gravados')) {
        el('resumo-cenarios-gravados').textContent = `${cenarios.length} de 2 opções gravadas neste contrato.`;
    }

    lista.innerHTML = cenarios.map((c, i) => `
        <div class="memorial-item" style="display:flex;justify-content:space-between;align-items:center;">
            <div>
                <small>OPÇÃO ${i + 1} • ${c.pisoCurto || ''}</small>
                <strong>${c.nome} — ${c.totalMaquinas} máq. (${c.qtdEscavadeiras}E + ${c.qtdCaminhoes}C | MF: ${c.matchFactor} | ${c.passadas} passes)</strong>
            </div>
            <div>
                <button type="button" class="btn-acao-tabela" data-acao="carregar" data-id="${c.id}" title="Carregar no formulário">🔄</button>
                <button type="button" class="btn-acao-tabela btn-excluir" data-acao="remover" data-id="${c.id}" title="Remover opção">✖</button>
            </div>
        </div>
    `).join('');
}

// Renderiza o parecer técnico e os 2 cards lado a lado na página comparativo_frota.html
async function renderizarPaginaComparativaDupla() {
    const container = el('container-comparativo-duplo');
    const parecerBox = el('parecer-tecnico-comparativo');
    if (!container) return;

    const cenarios = lerCache();
    if (!cenarios.length) {
        container.style.gridTemplateColumns = '1fr';
        container.innerHTML = `
            <div class="diagnostico-box" style="text-align:center;padding:40px;">
                <div class="diagnostico-titulo">Nenhuma opção gravada para comparação</div>
                <p style="color:#94a3b8;margin-top:8px;">Volte à tela de Dimensionamento de Frota, simule e grave até 2 opções.</p>
            </div>
        `;
        return;
    }

    const resp = await fetch('/api/comparar_cenarios', {
        method: 'POST',
        headers: obterHeadersJson(),
        body: JSON.stringify({ cenarios })
    });
    if (!resp.ok) {
        container.innerHTML = `<div class="diagnostico-box">Erro ao carregar comparativo (HTTP ${resp.status}).</div>`;
        return;
    }
    const data = await resp.json();

    // Exibe a recomendação técnica vinda do Python indicando qual cenário é mais vantajoso
    if (parecerBox && data.parecer) {
        alternarVisibilidade(parecerBox, true);
        parecerBox.innerHTML = `
            <div class="diagnostico-box" style="border-left:4px solid #22c55e;">
                <div class="diagnostico-titulo">🏆 Recomendação Técnica de Engenharia: ${data.recomendado || ''}</div>
                <p style="color:#e2e8f0;margin-top:6px;line-height:1.5;">${data.parecer}</p>
            </div>
        `;
    }

    // Renderiza os cards das opções lado a lado com botão individual para Infraestrutura
    container.innerHTML = (data.cards || []).map((card) => `
        <fieldset style="margin-bottom:0;border:2px solid ${card.corBorda};display:flex;flex-direction:column;gap:14px;">
            <legend>
                ${card.nome}
                ${card.badgeDestaque || ''}
            </legend>

            <div style="display:flex;justify-content:space-between;font-size:.9rem;color:#94a3b8;">
                <span>Piso: <strong style="color:#f8fafc;">${card.nomePiso}</strong></span>
                <span class="badge-classe">${card.badgeOpcao}</span>
            </div>

            <div class="subgrid-2">
                <div class="memorial-item"><small>Frota Carga & Transp.</small><strong>${card.totalMaquinas} máquinas (${card.qtdEscavadeiras}E + ${card.qtdCaminhoes}C • ${card.relacaoCamEscav || ''})</strong></div>
                <div class="memorial-item"><small>Match Factor</small><strong>MF ${card.matchFactor} (${card.passadas} passes)</strong></div>
            </div>

            <div class="card-equipamento">
                <div class="card-equipamento-header"><span class="titulo-eq">1. Carga (Escavadeiras)</span><strong>${card.qtdEscavadeiras}x</strong></div>
                <div style="font-size:.88rem;color:#cbd5e1;">${card.modEscav} (${card.cacamba} m³ • ${card.capCargaTH} t/h)</div>
            </div>

            <div class="card-equipamento">
                <div class="card-equipamento-header"><span class="titulo-eq">2. Transporte (Caminhões)</span><strong>${card.qtdCaminhoes}x</strong></div>
                <div style="font-size:.88rem;color:#cbd5e1;">${card.modCam} (${card.cargaCaminhao} t • ${card.capTranspTH} t/h)</div>
            </div>

            <div class="card-equipamento">
                <div class="card-equipamento-header"><span class="titulo-eq">3. Rodagem Anual</span><strong>${card.kmTotalHora} km/h</strong></div>
                <div style="font-size:.88rem;color:#cbd5e1;">${fmt(card.kmTotalAno)} km/ano (${card.passadas} passes/ciclo)</div>
            </div>

            <button type="button" class="btn-proximo no-print" data-infra-id="${card.id}" style="margin-top:auto;width:100%;">
                🚜 Dimensionar Infra com esta Opção ➔
            </button>
        </fieldset>
    `).join('');
}

// =========================================================================
// 7. INICIALIZAÇÃO E VINCULAÇÃO DE EVENTOS DA INTERFACE
// =========================================================================
document.addEventListener('DOMContentLoaded', () => {
    // Limpa automaticamente cenários antigos se o usuário veio de um novo planejamento
    const navEntry = performance.getEntriesByType('navigation')[0];
    const isPaginaPrincipal = !!el('form-dimensionamento');
    if (isPaginaPrincipal && navEntry?.type === 'navigate' && document.referrer.includes('planejamento')) {
        removerTodoCacheContrato();
    }

    renderizarTabelaComparativa();
    renderizarPaginaComparativaDupla();

    // Limpa os cenários automaticamente ao sair para o Planejamento ou Painel Principal
    document.querySelectorAll('.js-limpar-ao-sair').forEach((link) => {
        link.addEventListener('click', removerTodoCacheContrato);
    });

    // Eventos principais do formulário de dimensionamento
    el('perfil_piso')?.addEventListener('change', atualizarFatorEnchimentoPiso);
    el('btn-sugerir-frota')?.addEventListener('click', sugerirFrotaCompativel);
    el('btn-simular-frota')?.addEventListener('click', () => simularFrota());
    el('btn-salvar-cenario')?.addEventListener('click', salvarCenarioCache);
    el('btn-limpar-cenarios')?.addEventListener('click', limparCenariosCache);

    // Eventos da barra superior da página comparativa
    el('btn-fechar-aba')?.addEventListener('click', () => window.close());
    el('btn-imprimir-comparativo')?.addEventListener('click', () => window.print());

    // Atualização em tempo real do preview da escavadeira ao digitar
    document.querySelectorAll('[data-preview="escav"]').forEach((campo) => {
        campo.addEventListener('input', atualizarPreviewEscavadeira);
    });

    // Delegação de eventos nos botões de carregar/remover da lista resumida
    el('lista-mini-cenarios')?.addEventListener('click', (evento) => {
        const botao = evento.target.closest('button[data-acao]');
        if (!botao) return;

        const id = Number(botao.dataset.id);
        if (botao.dataset.acao === 'carregar') carregarCenarioNoFormulario(id);
        if (botao.dataset.acao === 'remover') removerCenarioCache(id);
    });

    // Delegação de eventos no botão "Dimensionar Infra com esta Opção" de cada card
    el('container-comparativo-duplo')?.addEventListener('click', (evento) => {
        const botao = evento.target.closest('button[data-infra-id]');
        if (!botao) return;

        abrirDimensionamentoInfra(Number(botao.dataset.infraId));
    });
});

// Garante atualização visual caso o usuário navegue usando o botão Voltar do navegador
window.addEventListener('pageshow', () => {
    renderizarTabelaComparativa();
    renderizarPaginaComparativaDupla();
});