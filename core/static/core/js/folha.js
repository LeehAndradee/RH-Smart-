let eventos = [];

document.addEventListener('DOMContentLoaded', () => {

    const funcionario = document.getElementById('funcionario');
    const salario = document.getElementById('salario_base');

    funcionario.addEventListener('change', () => {
        const selected = funcionario.options[funcionario.selectedIndex];
        salario.value = selected.dataset.salario || 0;
        calcular();
    });

});

function adicionarEvento() {
    const evento = document.getElementById('evento');
    const valorInput = document.getElementById('valor_evento');

    const nome = evento.options[evento.selectedIndex].text;
    const tipo = evento.options[evento.selectedIndex].dataset.tipo;
    let valor = parseFloat(valorInput.value);

    if (!valor) {
        valor = parseFloat(evento.options[evento.selectedIndex].dataset.valor || 0);
    }

    eventos.push({ nome, tipo, valor });

    atualizarLista();
    calcular();
}

function atualizarLista() {
    const lista = document.getElementById('lista_eventos');
    lista.innerHTML = '';

    eventos.forEach(e => {
        const li = document.createElement('li');
        li.innerText = `${e.nome} - R$ ${e.valor}`;
        lista.appendChild(li);
    });
}

function calcular() {
    let salario = parseFloat(document.getElementById('salario_base').value) || 0;

    let proventos = 0;
    let descontos = 0;

    eventos.forEach(e => {
        if (e.tipo === 'PROVENTO') proventos += e.valor;
        else descontos += e.valor;
    });

    let bruto = salario + proventos;

    let inss = bruto * 0.10; // simplificado
    let irrf = bruto * 0.05; // simplificado

    let liquido = bruto - inss - irrf - descontos;

    document.getElementById('bruto').innerText = bruto.toFixed(2);
    document.getElementById('inss').innerText = inss.toFixed(2);
    document.getElementById('irrf').innerText = irrf.toFixed(2);
    document.getElementById('liquido').innerText = liquido.toFixed(2);
}