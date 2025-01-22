import json
import os
from typing import List, Dict, Any
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
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

    def _analyze_step_type(self, text: str) -> str:
        """
        Analiza el texto del paso para determinar el tipo de paso Gherkin más apropiado.
        """
        text_lower = text.lower()
        
        # Analizar el contexto para determinar el tipo de paso
        if any(word in text_lower for word in ['mostrar', 'muestra', 'despliega', 'visualiza', '?se muestra']):
            return 'Then'
        elif any(word in text_lower for word in ['capturar', 'ingresar', 'escribir']):
            return 'When'
        elif any(word in text_lower for word in ['hacer clic', 'seleccionar', 'presionar']):
            return 'When'
        elif any(word in text_lower for word in ['verificar', 'validar', 'comprobar']):
            return 'Then'
        elif text_lower.startswith('?'):
            return 'Then'
        else:
            return 'When'

    def _format_step_content(self, text: str) -> str:
        """
        Formatea el contenido del paso, limpiando y truncando en saltos de línea.
        """
        # Remover el signo de interrogación al inicio si existe
        if text.startswith('?'):
            text = text[1:]
        
        # Eliminar comillas
        text = text.replace('"', '')
        
        # Tomar solo el texto hasta el primer salto de línea
        text = text.split('\n')[0]
        text = text.split('\\n')[0]
        
        # Lista de frases a eliminar (deben terminar en dos puntos)
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

    def _create_prompt(self, module: str, title: str, steps: List[Dict[str, Any]]) -> str:
        """
        Crea el prompt para el modelo de IA con mejor análisis de pasos.
        """
        feature_content = []
        feature_content.append(f"Feature: {module}")
        feature_content.append("")
        feature_content.append(f"  Scenario: {title}")
        
        # Ordenar los pasos por número
        sorted_steps = sorted(steps, key=lambda x: int(x['step_number']))
        
        current_type = None
        for step in sorted_steps:
            # Procesar paso principal
            paso = step['paso'].strip()
            if paso:
                formatted_content = self._format_step_content(paso)
                if formatted_content:
                    step_type = self._analyze_step_type(paso)
                    if step_type == current_type:
                        step_type = 'And'
                    current_type = step_type
                    feature_content.append(f"    {step_type} {formatted_content}")
            
            # Procesar validación
            validacion = step['validacion'].strip()
            if validacion:
                formatted_content = self._format_step_content(validacion)
                if formatted_content:
                    step_type = self._analyze_step_type(validacion)
                    if step_type == current_type:
                        step_type = 'And'
                    current_type = step_type
                    feature_content.append(f"    {step_type} {formatted_content}")
        
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
                    feature_filename = os.path.splitext(filename)[0].replace(' ', '_') + '.feature'
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