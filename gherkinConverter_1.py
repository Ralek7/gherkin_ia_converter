import json
import os
import re
from typing import List, Dict, Any
from transformers import pipeline, AutoTokenizer
import torch
import warnings
warnings.filterwarnings('ignore')

class SmartGherkinConverter:
    def __init__(self, input_dir: str, output_dir: str):
        """
        Inicializa el convertidor con IA usando GPT-2.
        
        Args:
            input_dir: Directorio con los archivos JSON de casos de prueba
            output_dir: Directorio de salida para los archivos .feature
        """
        self.input_dir = input_dir
        self.output_dir = output_dir
        
        # Inicializar el modelo
        print("Cargando modelo de IA...")   
        self.tokenizer = AutoTokenizer.from_pretrained('gpt2')
        # Configurar el pad token
        self.tokenizer.pad_token = self.tokenizer.eos_token
        
        self.generator = pipeline(
            'text-generation',
            model='gpt2',
            tokenizer=self.tokenizer,
            device_map="auto" if torch.cuda.is_available() else "cpu",
            truncation=True,
            padding=True,
        )
        print("Modelo cargado exitosamente")

    def _extract_flow_name(self, text: str) -> str:
        """
        Extrae el nombre del flujo del texto del primer paso.
        """
        # Buscar texto entre paréntesis
        parentesis_match = re.search(r'\((.*?)\)', text)
        if parentesis_match:
            return parentesis_match.group(1)
        
        # Buscar texto después de números y espacios
        numero_match = re.search(r'\d+\s+(.*?)(?:\(|$)', text)
        if numero_match:
            return numero_match.group(1).strip()
        
        return None

    def _format_step_content(self, text: str) -> str:
        """
        Formatea el contenido del paso, limpiando y truncando en saltos de línea.
        """
        if not text:
            return None
            
        # Remover el signo de interrogación al inicio si existe
        if text.startswith('?'):
            text = text[1:]
        
        # Eliminar comillas
        text = text.replace('"', '')
        
        # Lista de frases a eliminar
        frases_a_eliminar = [
            "con los campos:",
            "que devuelve:",
            "con el encabezado:",
            "con el mensaje:"
        ]
        
        # Eliminar las frases especificadas
        for frase in frases_a_eliminar:
            if text.endswith(frase):
                text = text[:-len(frase)].strip()
        
        # Si el texto está vacío o es solo espacios, retornar None
        if not text.strip():
            return None
            
        return text.strip()

    def _extract_clave_number(self, text: str) -> str:
        """
        Extrae el número de clave del texto.
        """
        match = re.search(r'Clave el numero (\d+)', text)
        if match:
            return match.group(1)
        return None

    def _create_prompt(self, module: str, title: str, steps: List[Dict[str, Any]]) -> str:
        """
        Crea el prompt para el modelo de IA con mejor análisis de pasos y AND statements.
        """
        feature_content = []
        feature_content.append(f"Feature: {module}")
        feature_content.append("")
        feature_content.append(f"  Scenario: {title}")
        
        # Ordenar los pasos por número
        sorted_steps = sorted(steps, key=lambda x: int(x['step_number']))
        
        # Extraer información del primer paso
        first_step = sorted_steps[0]['paso']
        last_step = sorted_steps[-1]['validacion'] if sorted_steps[-1]['validacion'] else sorted_steps[-1]['paso']
        
        # Formatear los pasos principales
        first_step_formatted = self._format_step_content(first_step)
        last_step_formatted = self._format_step_content(last_step)
        
        # Extraer número de clave y nombre del flujo
        clave_number = self._extract_clave_number(first_step_formatted)
        flow_name = self._extract_flow_name(first_step_formatted)
        
        # Generar Given
        if clave_number:
            feature_content.append(f"    Given Capturar en el campo Clave el numero {clave_number}")
        
        # Nuevas validaciones para AND statements
        beneficiary_patterns = [
            r"(?:Ingresa|Ingresar) (?:el )?(?:primer )?nombre del Cliente",
            r"(?:Ingresa|Ingresar) (?:el )?apellido paterno",
            r"(?:Ingresa|Ingresar) (?:el )?apellido materno"
        ]
        
        card_swipe_patterns = [
            r"[Dd]eslizar? (?:una )?tarjeta",
            r"[Dd]esliza (?:una )?tarjeta"
        ]
        
        # Patrones actualizados para cuenta y tarjeta
        account_patterns = [
            r"Capturar los siguientes datos:\s*\n?N[úu]mero de Cuenta \*\*<numero_cuenta>\*\*",
            r"Capturar los siguientes datos:\s*\n?N[úu]mero de Tarjeta \*\*<numero_tarjeta>\*\*",
            # Variaciones adicionales por si el formato varía ligeramente
            r"Capturar los siguientes datos:.*N[úu]mero de Cuenta.*\*\*.*\*\*",
            r"Capturar los siguientes datos:.*N[úu]mero de Tarjeta.*\*\*.*\*\*"
        ]
        
        # Patrones para detectar el desglose de efectivo
        desglose_patterns = [
            r"Capturar el registro total de efectivo que ingresa a la caja:",
            r"Capturar el registro total de efectivo que saldrá de la caja:",
            r"Capturar el registro total de efectivo que (?:ingresa|sale) (?:a|de) la caja:",
            r"Capturar el registro total de efectivo:",
            r"Capturar el desglose de efectivo:",
        ]
        
        # Verificar patrones en todos los pasos
        has_beneficiary = any(
            any(re.search(pattern, self._format_step_content(step['paso']) or '') 
                for pattern in beneficiary_patterns)
            for step in sorted_steps
        )
        
        has_card_swipe = any(
            any(re.search(pattern, self._format_step_content(step['paso']) or '')
                for pattern in card_swipe_patterns)
            for step in sorted_steps
        )
        
        # Modificada la verificación para account_patterns
        has_account = any(
            any(re.search(pattern, step['paso'] or '', re.DOTALL)  # Agregado re.DOTALL para manejar \n
                for pattern in account_patterns)
            for step in sorted_steps
        )
        
        # Verificación modificada para desglose usando el texto sin procesar
        has_desglose = any(
            any(re.search(pattern, step.get('paso', '') or '', re.IGNORECASE)
                for pattern in desglose_patterns)
            for step in sorted_steps
        )
        
        # Agregar AND statements antes del When
        if has_beneficiary:
            feature_content.append("    And ingresar datos correspondientes del beneficiario")
        
        if has_card_swipe:
            feature_content.append("    And deslizar tarjeta")
        
        if has_account:
            feature_content.append("    And ingresar numero de cuenta/tarjeta")
        
        # Generar When
        if flow_name:
            feature_content.append(f"    When realizar flujo de: {flow_name}")
        
        # Agregar AND statement después del When
        if has_desglose:
            feature_content.append("    And ingresar desglose efectivo")
        
        # Generar Then
        if last_step_formatted:
            last_step_clean = last_step_formatted
            if "se muestra" in last_step_clean.lower() or "se despliega" in last_step_clean.lower():
                feature_content.append(f"    Then {last_step_clean}")
            else:
                feature_content.append(f"    Then {flow_name} finalizado exitosamente")
        
        return "\n".join(feature_content)

    def _optimize_with_ai(self, module: str, title: str, steps: List[Dict[str, Any]]) -> str:
        """
        Usa el modelo para optimizar y generar el escenario Gherkin.
        """
        # Generar el contenido directamente sin usar el modelo
        return self._create_prompt(module, title, steps)

    def _read_json_file(self, file_path: str) -> Dict[str, Any]:
        """Lee y procesa un archivo JSON de caso de prueba."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Convertir el CasoPrueba a una lista de pasos ordenados
        steps = []
        for step_number, step_data in data["CasoPrueba"].items():
            step_data['step_number'] = step_number  # Agregar número de paso
            steps.append(step_data)
        
        return {
            'module': data["Modulo"],
            'title': data["Titulo"],
            'steps': steps
        }

    def convert(self):
        """Convierte los casos de prueba de JSON a archivos .feature usando IA."""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        # Procesar cada archivo JSON en el directorio de entrada
        for filename in os.listdir(self.input_dir):
            if filename.endswith('.json'):
                print(f"Procesando archivo: {filename}")
                try:
                    file_path = os.path.join(self.input_dir, filename)
                    data = self._read_json_file(file_path)
                    
                    # Generar el contenido
                    final_content = self._optimize_with_ai(
                        data['module'],
                        data['title'],
                        data['steps']
                    )
                    
                    # Crear nombre del archivo feature reemplazando espacios por _
                    feature_filename = os.path.splitext(filename)[0].replace(' ', '_')+'_v1' + '.feature'
                    output_file = os.path.join(self.output_dir, feature_filename)
                    
                    with open(output_file, "w", encoding="utf-8") as f:
                        f.write(final_content)
                    
                    print(f"Archivo generado: {output_file}")
                    
                except Exception as e:
                    print(f"Error procesando el archivo {filename}: {str(e)}")
                    continue


if __name__ == "__main__":
    converter = SmartGherkinConverter(
        "test_cases",  # Directorio con los archivos JSON
        "features"     # Directorio de salida
    )
    converter.convert()


