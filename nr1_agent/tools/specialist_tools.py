from langchain_core.tools import tool

@tool
def agendar_inspecao_interna(setor: str, detalhes: str) -> str:
    """
    Agenda uma inspeção de segurança interna em um setor específico.

    Use esta ferramenta quando um risco identificado puder ser avaliado e resolvido
    pela equipe de segurança do trabalho da própria empresa.

    Args:
        setor: O nome do setor onde a inspeção é necessária (ex: "Linha de Produção B", "Almoxarifado").
        detalhes: Uma descrição clara do motivo da inspeção e dos pontos a serem verificados.

    Returns:
        Uma mensagem de confirmação com o número do protocolo do agendamento.
    """
    # Simulação de agendamento em um sistema interno
    print(f"--- TOOL CALL: Agendando inspeção interna no setor '{setor}' ---")
    print(f"--- DETALHES: {detalhes} ---")
    protocolo = "INSP-2026-98765"
    return f"Agendamento de inspeção interna realizado com sucesso. Protocolo: {protocolo}."

@tool
def agendar_servico_externo(tipo_servico: str, detalhes: str) -> str:
    """
    Agenda um serviço especializado com um fornecedor externo.

    Use esta ferramenta para riscos que exigem uma avaliação ou intervenção
    que vai além da capacidade da equipe interna, como uma consultoria
    especializada em ergonomia ou uma avaliação de contaminação química.

    Args:
        tipo_servico: O tipo de serviço especializado necessário (ex: "Consultoria de Segurança Química", "Avaliação Ergonômica").
        detalhes: Uma descrição do problema e do serviço solicitado.

    Returns:
        Uma mensagem de confirmação do agendamento externo.
    """
    # Simulação de chamada de API para um sistema de fornecedores
    print(f"--- TOOL CALL: Acionando serviço externo de '{tipo_servico}' ---")
    print(f"--- DETALHES: {detalhes} ---")
    return "Serviço externo acionado com sucesso. O fornecedor entrará em contato para alinhar os detalhes."

if __name__ == '__main__':
    # Bloco para teste rápido e demonstração
    print("Testando a ferramenta de agendamento interno:")
    resultado_interno = agendar_inspecao_interna.invoke({
        "setor": "Usinagem",
        "detalhes": "Verificar proteção de torno mecânico relatado como defeituoso."
    })
    print(f"Resultado: {resultado_interno}\n")

    print("Testando a ferramenta de agendamento externo:")
    resultado_externo = agendar_servico_externo.invoke({
        "tipo_servico": "Análise de Ruído Ambiental",
        "detalhes": "Colaborador do setor de prensas relatou ruído excessivo. Necessário medições."
    })
    print(f"Resultado: {resultado_externo}")
