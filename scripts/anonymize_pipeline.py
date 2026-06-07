#!/usr/bin/env python3
"""
Anonymization Pipeline Module

This module provides anonymization functionality for personal information
in annotated documents. It replaces personal information with generated
synthetic data while maintaining annotation offset consistency.
"""

import json
import random
import string
import logging
from typing import Dict, List, Any, Tuple
from faker import Faker
from datetime import datetime, timedelta
from num2words import num2words

logger = logging.getLogger(__name__)


# ============================================================================
# Generator Functions for Personal Information Types
# ============================================================================

def gerar_names(genero=None):
    """Generate synthetic Portuguese names."""
    fake = Faker('pt_PT')
    if genero is None:
        genero = random.choice(["M", "F"])
    return fake.name_male() if genero == "M" else fake.name_female()


def gerar_admin():
    """Generate synthetic administrative codes."""
    ano = str(random.randint(2015, 2023))
    letras = string.ascii_uppercase
    formatos = [
        lambda: f"{''.join(random.choices(string.digits, k=5))}/{ano}",
        lambda: f"{''.join(random.choices(letras, k=4))}/{ano}/{''.join(random.choices(string.digits, k=4))}",
        lambda: f"{''.join(random.choices(string.digits, k=5))}-{''.join(random.choices(letras, k=2))}",
        lambda: f"{''.join(random.choices(string.digits, k=4))}",
        lambda: f"{''.join(random.choices(string.digits, k=2))}/{''.join(random.choices(string.digits, k=4))}-{''.join(random.choices(letras, k=1))}"
    ]
    return random.choice(formatos)()


def gerar_position(genero=None):
    """Generate synthetic job positions."""
    cargos_municipais = [
        {"cargo_feminino": "Chefe de Gabinete", "cargo_masculino": "Chefe de Gabinete"},
        {"cargo_feminino": "Coordenadora de Unidade", "cargo_masculino": "Coordenador de Unidade"},
        {"cargo_feminino": "Diretora de Departamento", "cargo_masculino": "Diretor de Departamento"},
        {"cargo_feminino": "Chefe da Divisão Administrativa", "cargo_masculino": "Chefe da Divisão Administrativa"},
        {"cargo_feminino": "Responsável do Mercado Municipal", "cargo_masculino": "Responsável do Mercado Municipal"},
        {"cargo_feminino": "Gestora do Contrato", "cargo_masculino": "Gestor do Contrato"},
        {"cargo_feminino": "Dirigente de Grau 3", "cargo_masculino": "Dirigente de Grau 3"},
        {"cargo_feminino": "Coordenadora do Gabinete Jurídico", "cargo_masculino": "Coordenador do Gabinete Jurídico"},
        {"cargo_feminino": "Diretora Municipal", "cargo_masculino": "Diretor Municipal"},
        {"cargo_feminino": "Chefe da Área de Fiscalização", "cargo_masculino": "Chefe da Área de Fiscalização"},
        {"cargo_feminino": "Secretária do Gabinete de Apoio", "cargo_masculino": "Secretário do Gabinete de Apoio"},
        {"cargo_feminino": "Vice-Presidente", "cargo_masculino": "Vice-Presidente"},
        {"cargo_feminino": "Chefe da Divisão Jurídica", "cargo_masculino": "Chefe da Divisão Jurídica"},
        {"cargo_feminino": "Coordenadora de Segurança", "cargo_masculino": "Coordenador de Segurança"},
        {"cargo_feminino": "Diretora de Serviços Partilhados", "cargo_masculino": "Diretor de Serviços Partilhados"},
    ]
    cargo_data = random.choice(cargos_municipais)
    if genero == 'F':
        return cargo_data["cargo_feminino"]
    return cargo_data["cargo_masculino"]


def gerar_address():
    """Generate synthetic Portuguese addresses."""
    fake = Faker('pt_PT')
    rua_faker = fake.street_name()

    termos_proibidos = ["Rua", "Avenida", "Travessa", "Calçada", "Alameda", "Praceta", "Praça", "Av", "R."]
    comeca_com_prefixo = any(rua_faker.lower().startswith(termo.lower()) for termo in termos_proibidos)

    if not comeca_com_prefixo:
        prefixo_obrigatorio = random.choice(["Rua", "Avenida", "Travessa", "Calçada", "Alameda"])
        rua_final = f"{prefixo_obrigatorio} {rua_faker}"
    else:
        rua_final = rua_faker

    cidade = fake.city()
    formatos = [
        lambda: f"{rua_final}, {fake.building_number()}, {cidade}",
        lambda: f"{rua_final}, {cidade}",
        lambda: f"{rua_final}, {fake.postcode()} {cidade}"
    ]

    return random.choice(formatos)()


def gerar_dates():
    """Generate synthetic dates."""
    inicio = datetime(2015, 1, 1)
    fim = datetime(2024, 12, 31)
    data_aleatoria = inicio + timedelta(days=random.randint(0, (fim - inicio).days))
    dia = data_aleatoria.day
    ano = data_aleatoria.year
    mes_nome = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"][data_aleatoria.month - 1]
    
    formatos = [
        lambda: data_aleatoria.strftime("%d/%m/%Y"),
        lambda: f"{dia:02d} de {mes_nome} de {ano}",
        lambda: f"{dia:02d} de {mes_nome}",
        lambda: f"{ano}",
        lambda: f"{num2words(dia, lang='pt_PT')} {'dia' if dia == 1 else 'dias'} do mês de {mes_nome} do ano de {num2words(ano, lang='pt_PT')}"
    ]
    return random.choice(formatos)()


def gerar_location():
    """Generate synthetic locations."""
    fake = Faker('pt_PT')
    return random.choice([fake.city, fake.administrative_unit, fake.country])()


def gerar_other():
    """Generate other synthetic personal information."""
    def cemiterio():
        num, fila, quart = random.randint(1, 500), random.randint(1, 20), random.randint(1, 10)
        return random.choice([
            f"Sepultura nº {num}, Fila {fila}, Quarteirão {quart}",
            f"Jazigo perpétuo nº {num}",
            f"Ossário {num}, Quadrante {quart}"
        ])

    def andares():
        return random.choice([
            f"{random.choice(['Rés-do-chão', 'Primeiro', 'Segundo', 'Terceiro', 'Quarto'])} {random.choice(['andar', 'piso'])}",
            f"Cave {random.randint(1, 3)}",
            f"Piso {random.randint(1, 10)}"
        ])

    def estado_civil():
        return random.choice([
            "solteiro", "casado", "divorciado", "viúvo", "união de facto",
            "solteira", "casada", "divorciada", "viúva"
        ])

    def titulos():
        return random.choice([
            "Sr.", "Sra.", "Dr.", "Dra.", "Eng.", "Eng.ª",
            "Prof.", "Prof.ª", "Arq.", "Arq.ª"
        ])

    def saude_tecnico():
        return random.choice([
            "Técnico de Diagnóstico e Terapêutica", "Enfermeiro Especialista",
            "Médico de Medicina Geral e Familiar"
        ])

    return random.choice([cemiterio, andares, estado_civil, titulos, saude_tecnico])()


def gerar_info():
    """Generate synthetic personal identification numbers."""
    digitos = string.digits
    letras = string.ascii_uppercase

    formatos = [
        lambda: ''.join(random.choices(digitos, k=9)),
        lambda: f"{''.join(random.choices(digitos, k=3))}.{''.join(random.choices(digitos, k=3))}.{''.join(random.choices(digitos, k=3))}",
        lambda: f"{''.join(random.choices(digitos, k=4))}/{''.join(random.choices(digitos, k=3))}",
        lambda: f"{random.choice(letras)}-{''.join(random.choices(digitos, k=4))}",
        lambda: f"{''.join(random.choices(digitos, k=8))} {random.choice(digitos)} {''.join(random.choices(letras, k=3))}"
    ]
    return random.choice(formatos)()


def gerar_company():
    """Generate synthetic company names."""
    fake = Faker('pt_PT')
    sufixos_pt = [
        "Lda.", "S.A.", "S.P.R.L.", "E.P.E.",
        "Limitada", "e Filhos, Lda.", "Unipessoal, Lda."
    ]

    formatos = [
        lambda: f"{fake.last_name()} & {fake.last_name()}, {random.choice(sufixos_pt)}",
        lambda: f"Construções {fake.city()}, {random.choice(sufixos_pt)}",
        lambda: f"{fake.name()} - {random.choice(['Consultoria', 'Serviços', 'Unipessoal, Lda.'])}",
        lambda: f"{random.choice(['Associação', 'Cooperativa', 'Sociedade'])} {random.choice(['Agrícola', 'Regional', 'Comercial'])} de {fake.city()}"
    ]
    return random.choice(formatos)()


def gerar_artistic():
    """Generate synthetic artistic terms."""
    artes_cenas = [
        "pintura", "escultura", "ilustração", "banda desenhada", "BD",
        "fotografia", "artes plásticas", "artes visuais", "serigrafia",
        "gravura", "arte digital", "pintura a óleo", "aguarela",
        "design gráfico", "arquitetura", "literatura", "poesia",
        "arte contemporânea", "instalação artística", "vídeo-arte",
        "exposição coletiva", "exposição individual", "bienal de artes",
        "concurso de ilustração", "residência artística", "ateliê",
    ]
    return random.choice(artes_cenas)


def gerar_degree():
    """Generate synthetic academic degrees."""
    graus = ["Licenciatura", "Mestrado", "Doutoramento", "Pós-Graduação"]
    areas = [
        "Direito", "Gestão", "Economia", "Engenharia Informática",
        "Engenharia Civil", "Engenharia Mecânica", "Medicina",
        "Arquitetura", "História", "Geografia", "Psicologia",
        "Ciências da Comunicação", "Administração Pública",
        "Relações Internacionais", "Biologia", "Enfermagem",
    ]
    especialidades = [
        "em Planeamento Territorial", "em Património Cultural",
        "em Sistemas de Informação", "em Intervenção Social",
        "em Gestão Autárquica", "em Finanças Públicas"
    ]

    formatos = [
        lambda: f"{random.choice(graus)} em {random.choice(areas)}",
        lambda: random.choice(areas),
        lambda: f"{random.choice(graus)} em {random.choice(areas)} {random.choice(especialidades)}",
        lambda: f"{random.choice(['Lic.', 'Mest.', 'Dout.'])} em {random.choice(areas)}"
    ]
    return random.choice(formatos)()


def gerar_time():
    """Generate synthetic times."""
    hora = random.randint(8, 21)
    minuto = random.randint(0, 59)

    formatos = [
        lambda: f"{hora:02d}:{minuto:02d}",
        lambda: f"{hora:02d} horas"
    ]

    return random.choice(formatos)()


def gerar_license():
    """Generate synthetic license plates."""
    def r_letras():
        return ''.join(random.choices(string.ascii_uppercase, k=2))
    
    def r_numeros():
        return ''.join(random.choices(string.digits, k=2))
    
    formatos = [
        lambda: f"{r_numeros()}-{r_numeros()}-{r_numeros()}",
        lambda: f"{r_numeros()}-{r_numeros()}-{r_letras()}",
        lambda: f"{r_numeros()}-{r_letras()}-{r_numeros()}",
        lambda: f"{r_letras()}-{r_numeros()}-{r_letras()}"
    ]

    return random.choice(formatos)()


def gerar_job():
    """Generate synthetic job titles."""
    fake = Faker('pt_PT')

    profissoes_atas = [
        "Assistente Operacional", "Assistente Técnico", "Técnico Superior",
        "Fiscal Municipal", "Chefe de Divisão", "Diretor de Departamento",
        "Arquiteto", "Engenheiro Civil", "Advogado", "Solicitador",
        "Cantoneiro", "Jardineiro", "Motorista de Pesados", "Polícia Municipal",
        "Professor", "Educador de Infância", "Médico", "Enfermeiro",
    ]

    formatos = [
        lambda: random.choice(profissoes_atas),
        lambda: fake.job(),
        lambda: fake.job().capitalize(),
    ]

    return random.choice(formatos)()


def gerar_vehicle():
    """Generate synthetic vehicle descriptions."""
    marcas_modelos = {
        "Renault": ["Clio", "Megane", "Captur"],
        "Volkswagen": ["Golf", "Polo", "Passat", "T-Roc"],
        "Peugeot": ["208", "3008", "508"],
        "BMW": ["Série 1", "Série 3", "X1"],
        "Mercedes-Benz": ["Classe A", "Classe C", "EQC"],
        "Citroën": ["C3", "C4", "Berlingo"],
        "Fiat": ["500", "Panda", "Tipo"],
        "Toyota": ["Yaris", "Corolla", "Hilux"]
    }

    cores = ["branco", "preto", "cinzento", "azul", "vermelho", "verde", "antracite"]
    combustiveis = ["gasolina", "gasóleo", "elétrico", "híbrido", "GPL"]
    cilindradas = ["1000 cc", "1200 cm3", "1500 cc", "1600 cm3", "1900 cc", "2000 cm3"]

    marca = random.choice(list(marcas_modelos.keys()))
    modelo = random.choice(marcas_modelos[marca])
    cor = random.choice(cores)
    cilindrada = random.choice(cilindradas)
    combustivel = random.choice(combustiveis)

    formatos = [
        lambda: f"{marca} {modelo}, {cilindrada}, cor {cor}",
        lambda: f"{marca} {modelo}, cor {cor}",
        lambda: f"{marca} {modelo}",
        lambda: f"{marca} {modelo}, {combustivel}, cor {cor}"
    ]

    return random.choice(formatos)()


def gerar_faculty(genero_contexto="M"):
    """Generate synthetic faculty/university names."""
    faculdades_portuguesas = [
        "Universidade de Lisboa", "Universidade do Porto", "Universidade de Coimbra",
        "Universidade do Minho", "Universidade de Aveiro", "Universidade de Évora",
        "Universidade do Algarve", "Universidade da Beira Interior",
        "Instituto Politécnico de Lisboa", "Instituto Politécnico do Porto",
        "Universidade Católica Portuguesa", "Universidade Lusófona",
    ]

    faculdade = random.choice(faculdades_portuguesas)

    if "Universidade" in faculdade or "Escola" in faculdade:
        artigo_interno = "da" if faculdade.startswith("Universidade da") else "do"
    else:
        artigo_interno = "do"

    formatos = [
        lambda: faculdade,
        lambda: f"Escola Superior de {random.choice(['Educação', 'Tecnologia', 'Saúde'])} {artigo_interno} {faculdade}" if "Politécnico" in faculdade else faculdade
    ]

    return random.choice(formatos)()


def gerar_family(genero="M"):
    """Generate synthetic family relationship terms."""
    femininos = [
        "mãe", "filha", "esposa", "mulher", "tia", "sobrinha",
        "avó", "neta", "prima", "sogra", "nora", "cunhada",
        "herdeira", "viúva", "tutelada"
    ]
    masculinos = [
        "pai", "filho", "esposo", "marido", "tio", "sobrinho",
        "avô", "neto", "primo", "sogro", "genro", "cunhado",
        "herdeiro", "viúvo", "tutelado"
    ]

    if genero == "F":
        termo = random.choice(femininos)
    else:
        termo = random.choice(masculinos)

    return termo


def gerar_public(text: str = None) -> str:
    """
    Handle public personal information that should be preserved.
    This includes elected official names, public meeting references, etc.
    Returns the original text unchanged.
    """
    # For public information, we return it unchanged
    # as it's already public record
    if text:
        return text
    return "[Informação Pública]"


# ============================================================================
# Main Anonymization Logic
# ============================================================================

# Mapping of personal info types to generator functions
GENERATOR_MAPPING = {
    "PERSONAL-DATE": gerar_dates,
    "PERSONAL-TIME": gerar_time,
    "PERSONAL-POSITION": gerar_position,
    "PERSONAL-NAME": gerar_names,
    "PERSONAL-DEGREE": gerar_degree,
    "PERSONAL-FACULTY": gerar_faculty,
    "PERSONAL-ADDRESS": gerar_address,
    "PERSONAL-LOCATION": gerar_location,
    "PERSONAL-FAMILY": gerar_family,
    "PERSONAL-JOB": gerar_job,
    "PERSONAL-VEHICLE": gerar_vehicle,
    "PERSONAL-LICENSE": gerar_license,
    "PERSONAL-ADMIN": gerar_admin,
    "PERSONAL-COMPANY": gerar_company,
    "PERSONAL-INFO": gerar_info,
    "PERSONAL-ARTISTIC": gerar_artistic,
    "PERSONAL-OTHER": gerar_other,
    "PERSONAL-PUBLIC": gerar_public,
}

# Entity types that support gender parameter
ENTIDADES_COM_GENERO = ["PERSONAL-NAME", "PERSONAL-POSITION", "PERSONAL-FAMILY", "PERSONAL-FACULTY"]


def detect_gender(text: str) -> str:
    """
    Simple heuristic to detect gender from text.
    Returns 'F' for feminine, 'M' for masculine.
    """
    text_lower = text.lower()
    
    # Feminine indicators
    feminine_indicators = ['dra.', 'eng.ª', 'prof.ª', 'sra.', 'diretora', 'coordenadora', 
                          'chefe', 'presidente', 'vereadora', 'secretária']
    
    # Check for feminine indicators
    if any(ind in text_lower for ind in feminine_indicators):
        # Additional check: words ending in 'a' are often feminine
        words = text.split()
        if words and words[-1].endswith('a'):
            return 'F'
    
    return 'M'  # Default to masculine


def anonymize_text_with_offsets(
    text: str, 
    personal_info_annotations: List[Dict[str, Any]]
) -> Tuple[str, List[Dict[str, int]]]:
    """
    Anonymize personal information in text and track offset changes.
    
    Args:
        text: Original document text
        personal_info_annotations: List of personal info annotations with:
            - text: original text
            - type: personal info type (e.g., "PERSONAL-NAME")
            - start: start position in original text
            - end: end position in original text
    
    Returns:
        Tuple of (anonymized_text, offset_mapping) where:
        - anonymized_text: Text with personal info replaced
        - offset_mapping: List of dicts with 'original_pos' and 'offset_delta'
    """
    if not personal_info_annotations:
        logger.info("No personal information to anonymize")
        return text, []
    
    # Sort annotations by start position
    sorted_annotations = sorted(personal_info_annotations, key=lambda x: x['start'])
    
    logger.info(f"Anonymizing {len(sorted_annotations)} personal information annotations")
    
    # Track replacements for offset calculation
    replacements = []
    current_text = text
    running_offset = 0  # Cumulative offset change
    
    for i, annotation in enumerate(sorted_annotations):
        original_start = annotation['start']
        original_end = annotation['end']
        pi_type = annotation.get('category', '')
        original_text = annotation.get('text', '')
        
        # Adjust positions based on previous replacements
        adjusted_start = original_start + running_offset
        adjusted_end = original_end + running_offset
        
        # Verify the text matches (sanity check)
        actual_text = current_text[adjusted_start:adjusted_end]
        if actual_text != original_text and original_text:
            logger.warning(
                f"Text mismatch at position {original_start}-{original_end}. "
                f"Expected: '{original_text}', Found: '{actual_text}'"
            )
        
        # Generate replacement based on type
        generator_func = GENERATOR_MAPPING.get(pi_type)
        
        if not generator_func:
            logger.warning(f"No generator for type '{pi_type}', skipping annotation at {original_start}-{original_end}")
            continue
        
        # Generate replacement (with gender detection if applicable)
        if pi_type in ENTIDADES_COM_GENERO:
            genero = detect_gender(original_text)
            # PERSONAL-FACULTY uses different parameter name
            if pi_type == "PERSONAL-FACULTY":
                replacement_text = generator_func(genero_contexto=genero)
            else:
                replacement_text = generator_func(genero=genero)
        elif pi_type == "PERSONAL-PUBLIC":
            # For public information, preserve original text
            replacement_text = generator_func(text=original_text)
        else:
            replacement_text = generator_func()
        
        # Replace text
        current_text = current_text[:adjusted_start] + replacement_text + current_text[adjusted_end:]
        
        # Calculate offset change
        length_change = len(replacement_text) - len(original_text)
        running_offset += length_change
        
        # Record replacement for offset mapping
        replacements.append({
            'original_start': original_start,
            'original_end': original_end,
            'new_start': adjusted_start,
            'new_end': adjusted_start + len(replacement_text),
            'offset_delta': running_offset,
            'original_text': original_text,
            'replacement_text': replacement_text
        })
        
        logger.debug(
            f"Replaced '{original_text}' with '{replacement_text}' "
            f"at position {original_start}-{original_end} (adjusted {adjusted_start}-{adjusted_start + len(replacement_text)})"
        )
    
    logger.info(f"Anonymization complete. Text length changed from {len(text)} to {len(current_text)}")
    
    # Create anonymized personal_info annotations
    anonymized_personal_info = []
    for replacement in replacements:
        # Find the original annotation
        original_annotation = next(
            (ann for ann in sorted_annotations 
             if ann['start'] == replacement['original_start'] and ann['end'] == replacement['original_end']),
            None
        )
        
        if original_annotation:
            anonymized_ann = original_annotation.copy()
            anonymized_ann['text'] = replacement['replacement_text']
            anonymized_ann['start'] = replacement['new_start']
            anonymized_ann['end'] = replacement['new_end']
            # Store original offsets temporarily for lookup (will be removed before final output)
            anonymized_ann['original_start'] = replacement['original_start']
            anonymized_ann['original_end'] = replacement['original_end']
            anonymized_personal_info.append(anonymized_ann)
    
    return current_text, replacements, anonymized_personal_info


def adjust_annotation_offsets(
    annotations: List[Dict[str, Any]], 
    replacements: List[Dict[str, int]],
    exclude_types: List[str] = None
) -> List[Dict[str, Any]]:
    """
    Adjust annotation offsets based on text replacements.
    
    Args:
        annotations: List of annotations with 'start' and 'end' fields
        replacements: List of replacement records from anonymize_text_with_offsets
        exclude_types: List of annotation types to exclude from adjustment (e.g., personal info)
    
    Returns:
        List of annotations with adjusted offsets
    """
    if not replacements:
        return annotations
    
    exclude_types = exclude_types or []
    adjusted_annotations = []
    
    for annotation in annotations:
        # Skip personal info annotations (they've been replaced)
        if annotation.get('type') in exclude_types:
            continue
        
        original_start = annotation.get('start')
        original_end = annotation.get('end')
        
        if original_start is None or original_end is None:
            adjusted_annotations.append(annotation)
            continue
        
        # Find the offset delta to apply to START position
        # This is the cumulative delta from all replacements that ended before this annotation starts
        start_offset_delta = 0
        
        # Find the offset delta to apply to END position
        # This includes replacements that occur INSIDE the annotation
        end_offset_delta = 0
        
        for replacement in replacements:
            # If replacement ended before annotation start, affects both start and end
            if replacement['original_end'] <= original_start:
                start_offset_delta = replacement['offset_delta']
                end_offset_delta = replacement['offset_delta']
            # If replacement starts before annotation end (but after start), affects only end
            elif replacement['original_start'] < original_end:
                # This replacement is inside or overlaps the annotation
                end_offset_delta = replacement['offset_delta']
        
        # Create adjusted annotation (preserve original offsets for lookup)
        adjusted_annotation = annotation.copy()
        adjusted_annotation['original_start'] = original_start  # Keep original for lookup
        adjusted_annotation['original_end'] = original_end      # Keep original for lookup
        adjusted_annotation['start'] = original_start + start_offset_delta
        adjusted_annotation['end'] = original_end + end_offset_delta
        
        adjusted_annotations.append(adjusted_annotation)
    
    logger.info(f"Adjusted {len(adjusted_annotations)} annotations")
    
    return adjusted_annotations


def anonymize_document(
    text: str,
    personal_info_annotations: List[Dict[str, Any]],
    all_annotations: List[Dict[str, Any]] = None
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Main function to anonymize a document and adjust all annotations.
    
    Args:
        text: Original document text
        personal_info_annotations: List of personal info annotations to anonymize
        all_annotations: Optional list of all annotations to adjust offsets
    
    Returns:
        Tuple of (anonymized_text, adjusted_annotations, anonymized_personal_info)
    """
    # Anonymize text and get offset mapping
    anonymized_text, replacements, anonymized_personal_info = anonymize_text_with_offsets(text, personal_info_annotations)
    
    # Adjust other annotations if provided
    adjusted_annotations = []
    if all_annotations:
        # Get list of personal info types to exclude
        personal_info_types = {ann.get('type') for ann in personal_info_annotations}
        adjusted_annotations = adjust_annotation_offsets(
            all_annotations, 
            replacements,
            exclude_types=list(personal_info_types)
        )
    
    return anonymized_text, adjusted_annotations, anonymized_personal_info
