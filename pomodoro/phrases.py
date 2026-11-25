"""Frases de mindfulness do alarme.

Inspiradas nas ideias centrais de "Manual Prático Mindfulness: Curiosidade e
Aceitação" (Demarzo e Garcia Campayo).
"""

import random

PHRASES = [
    "Respire. A respiração está sempre no presente: use-a como âncora.",
    "Perceber que a mente divagou já é o momento mindful. Volte à âncora com gentileza.",
    "Mindfulness não é esvaziar a mente nem suprimir emoções. É observar com curiosidade e aceitação.",
    "Prática dos três minutos: 1) note o ambiente, o corpo e o que sente; 2) siga a respiração; 3) expanda a consciência.",
    "Pensamento intenso? Diga a ele: oi, obrigado e tchau. Ele passa.",
    "Saia do modo fazer e entre no modo ser por alguns instantes. Depois volte, por escolha.",
    "Não controle a respiração. Apenas observe como ela é agora.",
    "Regularidade vale mais que intensidade: poucos minutos, todos os dias.",
    "Corpo e respiração vivem no presente. Quando se perder, volte a eles.",
    "Sofrimento = dor x resistência. Aceitar não é aprovar; é parar de lutar com o que não controla.",
    "Pensamentos são transitórios, não são verdades e não têm poder próprio.",
    "Como você entra e sai da prática importa mais do que o que acontece durante ela.",
    "Saia da prática devagar, sem ruptura entre a meditação e a vida diária.",
    "Qual é a sua experiência agora? Que pensamentos, sensações e emoções estão presentes?",
    "Emoção difícil? Ancore a atenção nas sensações do corpo e observe-as mudar.",
    "Caminhe com atenção plena: sinta os pés no chão, o ritmo dos passos, o ar no rosto.",
    "Transforme tempo ocioso em prática: fila, elevador, espera, deslocamento.",
    "Divida o dia em períodos e defina uma intenção concreta de atenção para cada um.",
    "Uma postura ereta e digna já muda a mente. Sente-se com conforto e presença.",
    "Olhe para esta pausa com mente de principiante, como se fosse a primeira vez.",
    "Compaixão: deseje que todos os seres, inclusive você, sejam felizes e livres do sofrimento.",
    "A autocrítica ativa o sistema de ameaça. A gentileza consigo mesmo acalma.",
    "Inquieto? Alongue a expiração. Se não der para sentar, medite caminhando.",
    "Os acontecimentos são ambíguos; é a interpretação que os torna bons ou maus.",
    "Observe o diálogo interno sem acreditar em tudo o que ele diz.",
    "Um valor importante merece tempo. O que você fez hoje é coerente com o que importa para você?",
    "Faça a próxima tarefa como a prática da uva-passa: olhe, toque, sinta, com toda a curiosidade.",
    "As dificuldades na prática são oportunidades. Encare-as com equanimidade.",
    "Deixou de praticar? É só uma fase do aprendizado. Recomece agora.",
    "Dois sinais de boa prática: perceber rápido que divagou e voltar sem se irritar.",
    "Meditamos para levar a atenção plena ao resto do dia.",
    "Escaneie o corpo: dos pés à cabeça, note as sensações, sem precisar mudá-las.",
    "A realidade é como é. Aja no que for útil e solte o resto.",
    "Antes de retomar, três respirações conscientes: inspira, expira, presente.",
    "Lembretes ajudam a manter a prática. Este alarme é seu convite para voltar ao agora.",
    "Pensar com consciência cria distância; pensar no automático prende. Escolha olhar.",
    "Mindfulness tem dois pilares: regular a atenção e abrir-se à experiência.",
    "Dor faz parte da vida. O sofrimento vem de esperar que ela não exista.",
    "Observe o que o corpo pede agora: água, movimento, descanso, alongamento.",
    "Expanda a consciência: do corpo à sala, da sala à cidade, da cidade ao mundo.",
]

_bag = []


def next_phrase():
    """Saco sem reposição: nenhuma frase repete até todas aparecerem."""
    if not _bag:
        _bag.extend(range(len(PHRASES)))
        # Fisher-Yates
        for i in range(len(_bag) - 1, 0, -1):
            j = random.randint(0, i)
            _bag[i], _bag[j] = _bag[j], _bag[i]
    return PHRASES[_bag.pop()]
