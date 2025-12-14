import json
import os
from openai import OpenAI
from dotenv import load_dotenv

# 1. Configuración y Cliente de OpenAI
# Carga las variables del .env donde debe estar tu OPENAI_API_KEY
load_dotenv()
client = OpenAI()

# --- 2. ESQUEMAS JSON (DICCIONARIOS DE PYTHON PARA AYUDA VISUAL Y LÓGICA) ---
# Se mantienen definidos para:
# a) Usarlos como guía en el SYSTEM_PROMPT.
# b) Usar sus estructuras en la lógica del backend (aunque no se pasen directamente a la API).

JSON_SCHEMA_ESTRICTO = {
    "type": "object",
    "properties": {
        "merchant_name": {"type": "string", "description": "Nombre del merchant, e.g., 'Zoop'"},
        "lifecycle_stage": {"type": "string", "description": "Etapa: 'Lead', 'Negociación', 'Integración', 'Go-Live'"},
        "commercial_commitments": {"type": "string", "description": "Resumen de tasas, periodos de prueba o promesas de negocio."},
        "key_contacts": {
            "type": "object",
            "properties": {
                "Ventas": {"type": "string"}, 
                "Tech": {"type": "string"}
            }
        },
        "technical_restrictions": {
            "type": "array", 
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "description": "Ej: 'Riesgo', 'Seguridad', 'Integración'"}, 
                    "detail": {"type": "string", "description": "Descripción de la restricción o límite."}, 
                    "source_reference": {"type": "string", "description": "Ej: 'Slack 2024-10-25'"} 
                }
            }
        },
        "geographies_mops": {
            "type": "array", 
            "items": {
                "type": "object",
                "properties": {
                    "country": {"type": "string"},
                    "mops": {"type": "array", "items": {"type": "string"}},
                    "fraud_risk_level": {"type": "string"}
                }
            }
        },
        "pending_tasks": {"type": "array", "items": {"type": "string"}}
    }
}

JSON_OUTPUT_FILTRO = {
    "type": "object",
    "properties": {
        "business_answer": {"type": "string", "description": "Respuesta concisa y profesional de negocio."},
        "visualization_filter": {
            "type": "object",
            "properties": {
                "field": {"type": "string", "description": "Campo del JSON principal a filtrar (ej: 'technical_restrictions')"}, 
                "value": {"type": "string", "description": "Valor a destacar (ej: 'Riesgo', 'Mexico')"}
            }
        }
    }
}


# --- 3. PROMPT MAESTRO (Instrucciones para la IA) ---
# Se inyecta la representación del JSON Schema estricto dentro del prompt para guiar a la IA.
SYSTEM_PROMPT_MAESTRO = f"""
Eres el "Yuno Context Core", el Agente de Inteligencia de Negocios de Yuno. Tu rol es transformar información dispersa en decisiones de negocio, actuando en tres modos distintos basados en la instrucción del usuario.

# MODO 1: CONDENSACIÓN DE DATOS (INPUT: Texto Bruto/Notas)
# Objetivo: Extraer y estructurar datos nuevos.
# Output: Genera SOLO el objeto JSON que sigue el Esquema Estricto a continuación.

# MODO 2: GENERACIÓN DE CAMPOS SALESFORCE (INPUT: "Genera campos Salesforce...")
# Objetivo: Usar el JSON de Contexto (Memoria Viva) para crear texto listo para copiar.
# Output: Texto formateado para copy-paste (Ej: Markdown).

# MODO 3: CONSULTA DE NEGOCIO Y FILTRO (INPUT: Preguntas de Negocio)
# Objetivo: Responder y sugerir un filtro para el dashboard.
# Output: Genera SOLO el objeto JSON de Respuesta y Filtro.

---
ESQUEMA JSON ESTRICTO (Para la Memoria Viva del MODO 1):
{json.dumps(JSON_SCHEMA_ESTRICTO, indent=2)}

ESQUEMA DE RESPUESTA Y FILTRO (Para el MODO 3):
{json.dumps(JSON_OUTPUT_FILTRO, indent=2)}
"""

# --- 4. LÓGICA CENTRAL DE EJECUCIÓN ---

def execute_yuno_core(mode: int, input_data: str, current_context: dict = None):
    """
    Ejecuta el Agente Yuno Context Core en uno de sus tres modos.
    """
    
    user_prompt = ""
    response_format = {"type": "text"} 
    # Usamos gpt-4-turbo o gpt-4o para garantizar la calidad y precisión.
    model = "gpt-4-turbo" 

    # --- Construcción del Prompt y Formato ---
    if mode == 1:
        # MODO 1: CONDENSACIÓN
        user_prompt = f"Activa el MODO 1. Extrae y estructura el siguiente texto de comunicación de un merchant. Devuelve SOLAMENTE el JSON. TEXTO: {input_data}"
        # CORRECCIÓN: Quitamos 'schema' para evitar el error 400. Confiamos en el Prompt Maestro.
        response_format = {"type": "json_object"} 
        
    elif mode == 2:
        # MODO 2: SALESFORCE
        if not current_context:
            return "Error: Contexto del Merchant (Memoria Viva) requerido para MODO 2."
        user_prompt = f"""
        Activa el MODO 2. Genera los campos de Salesforce listos para copiar y pegar, 
        basándote SÓLO en el JSON de contexto adjunto.
        
        JSON DE CONTEXTO: {json.dumps(current_context, indent=2)}
        """

    elif mode == 3:
        # MODO 3: CONSULTA Y FILTRO
        if not current_context:
            return "Error: Contexto del Merchant (Memoria Viva) requerido para MODO 3."
        user_prompt = f"""
        Activa el MODO 3. Responde a la pregunta y genera el filtro JSON para el dashboard. 
        PREGUNTA: {input_data}
        
        JSON DE CONTEXTO: {json.dumps(current_context, indent=2)}
        """
        # CORRECCIÓN: Quitamos 'schema' para evitar el error 400. Confiamos en el Prompt Maestro.
        response_format = {"type": "json_object"} 
        
    else:
        return f"Modo de operación {mode} no reconocido."

    # --- Llamada a la API ---
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_MAESTRO},
                {"role": "user", "content": user_prompt}
            ],
            response_format=response_format 
        )
        
        raw_output = completion.choices[0].message.content
        
        if mode == 1 or mode == 3:
            # Los Modos 1 y 3 devuelven JSON que hay que parsear
            return json.loads(raw_output)
        
        return raw_output # El Modo 2 devuelve el texto directo

    except Exception as e:
        return f"Error en la llamada a la API de OpenAI: {e}"
    

    # Nueva función para core_api.py

def identify_merchant_from_text(text_snippet: str):
    """
    Usa la IA para identificar el nombre del merchant a partir de un fragmento de texto.
    """
    routing_prompt = f"""
    Eres un Agente de Routing de Yuno. Analiza el siguiente fragmento de texto e identifica SOLAMENTE el nombre del merchant al que se refiere. 
    Tu respuesta debe ser UN ÚNICO NOMBRE. Si no puedes identificarlo, responde 'DESCONOCIDO'.

    FRAGMENTO: "{text_snippet[:1000]}..."
    """
    try:
        client = OpenAI()
        completion = client.chat.completions.create(
            model="gpt-4o-mini", # Rápido y barato para routing
            messages=[
                {"role": "system", "content": routing_prompt},
                {"role": "user", "content": "Identifica el merchant."}
            ],
            temperature=0.0 # Búsqueda de un solo hecho
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error en el routing de merchant: {e}")
        return "ERROR_ROUTING"


# Coloca estas dos funciones ANTES del bloque 'if __name__ == "__main__":'

def get_context_filename(merchant_name: str) -> str:
    """Genera el nombre del archivo basado en el nombre del merchant."""
    # Normaliza el nombre del merchant para usarlo como nombre de archivo
    safe_name = merchant_name.replace(" ", "_").lower()
    return f"memory_{safe_name}.json"

def load_context(merchant_name: str) -> dict:
    """Carga el contexto del merchant desde el disco (simulación de DB)."""
    filename = get_context_filename(merchant_name)
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            # Si el archivo está corrupto, devuelve un contexto base
            return {"merchant_name": merchant_name, "lifecycle_stage": "Desconocido", "technical_restrictions": [], "geographies_mops": [], "commercial_commitments": ""}
    # Devuelve un contexto base si no existe
    return {"merchant_name": merchant_name, "lifecycle_stage": "Lead", "technical_restrictions": [], "geographies_mops": [], "commercial_commitments": ""}

def save_context(data: dict):
    """Guarda el contexto actualizado del merchant en el disco."""
    merchant_name = data.get("merchant_name", "unknown")
    if merchant_name != "unknown":
        filename = get_context_filename(merchant_name)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"   [PERSISTENCIA] Contexto de '{merchant_name}' guardado en '{filename}'")

# También debes asegurar que 'os' y 'json' estén importados al principio de core_api.py

# --- 5. BLOQUE DE PRUEBA DE FUNCIONALIDAD (Ejecución en Consola) ---
# --- 5. BLOQUE DE PRUEBA DE FUNCIONALIDAD (Ejecución en Consola) ---
if __name__ == '__main__':
    print("--- 🧠 YUNO CONTEXT CORE API PRUEBAS ---")

    # --- SIMULACIÓN DE ARCHIVO DE ENTRADA (Una nueva nota o transcripción) ---
    archivo_input_simulado = """
    Documento de seguimiento del Vendedor: La cuenta Zoop está en Negociación. El contacto de Ventas es Maria@zoop.com. 
    Se confirmó que la restricción de límite de $500 USD es para Colombia, no México. La implementación de PSE se mantiene.
    """
    
    # PASO 1: ROUTING - Identificar el Merchant
    print("\n--- PASO 1: ROUTING DE ARCHIVO ---")
    merchant_name = identify_merchant_from_text(archivo_input_simulado)
    print(f"✅ MERCHANT IDENTIFICADO: {merchant_name}")
    
    if merchant_name not in ["DESCONOCIDO", "ERROR_ROUTING"]:
        
        # PASO 2: CARGAR MEMORIA - Cargar la versión anterior del JSON (si existe)
        memoria_viva_existente = load_context(merchant_name)
        print(f"   [CARGA] Etapa anterior: {memoria_viva_existente.get('lifecycle_stage')}")
        
        # PASO 3: CONDENSACIÓN - Usar el MODO 1 para actualizar y consolidar la Memoria
        print("\n--- PASO 3: MODO 1 (ACTUALIZAR MEMORIA VIVA) ---")
        
        # Le enviamos el texto del archivo AÑADIENDO el contexto anterior para que la IA CONSOLIDE
        consolidated_input = f"""
        CONTEXTO ANTERIOR DEL MERCHANT {merchant_name}: {json.dumps(memoria_viva_existente, ensure_ascii=False)}
        NUEVO TEXTO DE ARCHIVO: {archivo_input_simulado}
        """
        
        memoria_viva_actualizada = execute_yuno_core(mode=1, input_data=consolidated_input)
        
        if isinstance(memoria_viva_actualizada, dict):
            print("✅ MODO 1 ÉXITO. Memoria Viva ACTUALIZADA y Consolidada.")
            
            # PASO 4: PERSISTENCIA - Guardar la nueva versión
            save_context(memoria_viva_actualizada)

            # PASO 5: SALESFORCE - MODO 2 (Usa la data guardada)
            print("\n--- PASO 5: MODO 2 (SALESFORCE FILLER) ---")
            salesforce_output = execute_yuno_core(mode=2, input_data="Generar campos de resumen para Salesforce.", current_context=memoria_viva_actualizada)
            print("✅ MODO 2 ÉXITO. Output Salesforce:\n" + salesforce_output)
            
            # PASO 6: CONSULTA - MODO 3 (Usa la data guardada)
            print("\n--- PASO 6: MODO 3 (CONSULTA Y FILTRO) ---")
            pregunta_negocio = "¿Cuál es el contacto de ventas y dónde está la restricción de $500 USD?"
            consulta_output = execute_yuno_core(mode=3, input_data=pregunta_negocio, current_context=memoria_viva_actualizada)
            
            if isinstance(consulta_output, dict):
                 print("✅ MODO 3 ÉXITO. Filtro Sugerido:", consulta_output.get("visualization_filter"))
        else:
            print(f"❌ FALLO EN CONDENSACIÓN: {memoria_viva_actualizada}")

### 3. Ejecución Final

