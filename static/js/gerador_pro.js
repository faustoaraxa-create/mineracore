document.addEventListener('DOMContentLoaded', () => {
    const containerPassos = document.getElementById('containerPassos');
    const corpoTabelaRiscos = document.getElementById('corpoTabelaRiscos');
    const botaoAdicionarPasso = document.getElementById('botaoAdicionarPasso');
    const botaoAdicionarRisco = document.getElementById('botaoAdicionarRisco');
    const botaoGerarDocumento = document.getElementById('botaoGerarDocumento');
    const botaoLimparFormulario = document.getElementById('botaoLimparFormulario');
    const campoDataDocumento = document.getElementById('dataDocumento');

    campoDataDocumento.valueAsDate = new Date();

    function renumerarPassos() {
        const cartoesPassos = containerPassos.querySelectorAll('.cartao-passo');
        cartoesPassos.forEach((cartao, indice) => {
            const tituloPasso = cartao.querySelector('.numero-passo');
            tituloPasso.textContent = `Passo ${indice + 1}`;
        });
    }

    function adicionarNovoPasso(descricaoInicial = '', pontoAtencaoInicial = '') {
        const cartaoPasso = document.createElement('div');
        cartaoPasso.className = 'cartao-passo';

        cartaoPasso.innerHTML = `
            <div class="cabecalho-passo">
                <span class="numero-passo">Passo</span>
                <button type="button" class="botao-remover nao-imprimir">Remover</button>
            </div>
            <div class="conteudo-passo">
                <div class="campos-texto-passo">
                    <div class="grupo-campo">
                        <label>Descrição da Ação (O que e como fazer):</label>
                        <textarea rows="2" placeholder="Descreva a ação detalhada desta etapa...">${descricaoInicial}</textarea>
                    </div>
                    <div class="grupo-campo margem-topo">
                        <label>Ponto de Atenção / Critério de Verificação:</label>
                        <input type="text" value="${pontoAtencaoInicial}" placeholder="Ex: Verificar pressão, conferir alinhamento, confirmar via rádio...">
                    </div>
                </div>
                <div class="area-imagem-passo sem-imagem">
                    <label class="nao-imprimir" style="font-size: 10px; color: #475569; margin-bottom: 4px;">Foto / Ilustração (Opcional)</label>
                    <input type="file" accept="image/*" class="nao-imprimir input-imagem">
                    <img class="preview-imagem" alt="Imagem do passo">
                </div>
            </div>
        `;

        const botaoRemover = cartaoPasso.querySelector('.botao-remover');
        botaoRemover.addEventListener('click', () => {
            cartaoPasso.remove();
            renumerarPassos();
        });

        const inputImagem = cartaoPasso.querySelector('.input-imagem');
        const previewImagem = cartaoPasso.querySelector('.preview-imagem');
        const areaImagem = cartaoPasso.querySelector('.area-imagem-passo');

        inputImagem.addEventListener('change', (evento) => {
            const arquivo = evento.target.files[0];
            if (arquivo) {
                const leitor = new FileReader();
                leitor.onload = (e) => {
                    previewImagem.src = e.target.result;
                    previewImagem.style.display = 'block';
                    areaImagem.classList.remove('sem-imagem');
                };
                leitor.readAsDataURL(arquivo);
            } else {
                previewImagem.src = '';
                previewImagem.style.display = 'none';
                areaImagem.classList.add('sem-imagem');
            }
        });

        containerPassos.appendChild(cartaoPasso);
        renumerarPassos();
    }

    function adicionarLinhaRisco() {
        const linha = document.createElement('tr');
        linha.innerHTML = `
            <td><textarea rows="2" placeholder="Ex: Queda de material / Ponto de prensamento..."></textarea></td>
            <td><textarea rows="2" placeholder="Ex: Manter distância segura, realizar bloqueio..."></textarea></td>
            <td><textarea rows="2" placeholder="Ex: Paralisar atividade imediatamente e acionar supervisão..."></textarea></td>
            <td class="nao-imprimir" style="text-align: center;">
                <button type="button" class="botao-remover">X</button>
            </td>
        `;

        const botaoRemover = linha.querySelector('.botao-remover');
        botaoRemover.addEventListener('click', () => {
            linha.remove();
        });

        corpoTabelaRiscos.appendChild(linha);
    }

    document.addEventListener('input', (evento) => {
        if (evento.target.tagName.toLowerCase() === 'textarea') {
            evento.target.style.height = 'auto';
            evento.target.style.height = evento.target.scrollHeight + 'px';
        }
    });

    botaoAdicionarPasso.addEventListener('click', () => adicionarNovoPasso());
    botaoAdicionarRisco.addEventListener('click', () => adicionarLinhaRisco());

    botaoGerarDocumento.addEventListener('click', () => {
        window.print();
    });

    botaoLimparFormulario.addEventListener('click', () => {
        if (confirm('Deseja realmente limpar todos os campos do procedimento?')) {
            document.querySelectorAll('input[type="text"], textarea').forEach(campo => {
                campo.value = '';
                if (campo.tagName.toLowerCase() === 'textarea') {
                    campo.style.height = 'auto';
                }
            });
            document.getElementById('revisaoDocumento').value = '00';
            campoDataDocumento.valueAsDate = new Date();
            containerPassos.innerHTML = '';
            corpoTabelaRiscos.innerHTML = '';
            adicionarNovoPasso();
            adicionarLinhaRisco();
        }
    });

    adicionarNovoPasso();
    adicionarLinhaRisco();
});