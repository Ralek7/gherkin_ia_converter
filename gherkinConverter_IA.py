import json
import os
import re
import textwrap
import time
from typing import Dict, Any
import unicodedata
from transformers import pipeline # Nueva dependencia

class UltimateGherkinConverterAI:
    def __init__(self, input_dir: str, output_dir: str):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.nlp_classifier = pipeline("zero-shot-classification", 
                                     model="facebook/bart-large-mnli") # Modelo para clasificación
        self.step_generator = pipeline("text-generation", 
                                     model="gpt2-medium") # Modelo para generación de textos
        
        print("Inicializando IA...")
        time.sleep(2)

    def _clean_text(self, text: str) -> str:
        # Implementación original conservada
        return re.sub(r'[^\wá-úÁ-Ú \n\-]', '', text, flags=re.IGNORECASE).strip()

    def _is_valid_step(self, text: str) -> bool:
        # Implementación original conservada
        return len(text) > 2 and not re.match(r'^[\d\W]+$', text)

    def _ai_classify_step(self, text: str) -> str:
        """Clasificación de pasos usando IA"""
        candidate_labels = ["Given", "When", "Then", "And"]
        result = self.nlp_classifier(text, candidate_labels)
        return result['labels'][0]

    def _ai_enhance_step(self, step: str, context: str) -> str:
        """Mejora de redacción con IA (versión corregida)"""
        prompt = f"""Mejora este paso de testing manteniendo su significado:
        Original: {step}
        Contexto: {context}
        Versión mejorada:"""
        
        generated = self.step_generator(
            prompt, 
            max_new_tokens=100,  # Cambiar de max_length
            num_return_sequences=1,
            temperature=0.7,
            truncation=True,  # Añadir truncamiento explícito
            pad_token_id=self.step_generator.tokenizer.eos_token_id  # Solucionar warning de padding
        )
        return generated[0]['generated_text'].split("Versión mejorada:")[-1].strip()

    def _process_steps(self, raw_steps: Dict, module: str, title: str) -> Dict[str, Any]:
        """Procesamiento híbrido IA + reglas"""
        try:
            sorted_steps = sorted(
                ({'key': int(k), **v} for k, v in raw_steps.items()),
                key=lambda x: x['key']
            )
        except:
            sorted_steps = list(raw_steps.values())

        if not sorted_steps:
            return {
                'Given': 'Iniciar flujo',
                'When': 'Ejecutar proceso',
                'Then': 'Proceso finalizado exitosamente',
                'And': []
            }

        # Clasificación IA de cada paso
        ai_classified = []
        for step in sorted_steps:
            raw_text = f"{step.get('paso', '')} {step.get('validacion', '')}"
            classified = self._ai_classify_step(raw_text)
            ai_classified.append((classified, raw_text))

        # Lógica híbrida para estructura Gherkin
        given_candidates = [t for c, t in ai_classified if c == "Given"]
        when_candidates = [t for c, t in ai_classified if c == "When"]
        then_candidates = [t for c, t in ai_classified if c == "Then"]
        
        # Fallback a lógica original si IA no detecta suficientes
        given = given_candidates[0] if given_candidates else next(
            (f"Iniciar proceso: {self._clean_text(s['paso'])}" 
             for s in sorted_steps if s.get('paso')), 
            "Iniciar flujo"
        )

        when = when_candidates[0] if when_candidates else self._create_action_summary(
            [self._clean_text(s['paso']) for s in sorted_steps[1:-1] if s.get('paso')]
        )[0]

        then = then_candidates[-1] if then_candidates else next(
            (self._clean_text(s.get('validacion', '')) 
             for s in reversed(sorted_steps) 
             if self._is_valid_step(s.get('validacion', ''))),
            'Proceso finalizado exitosamente'
        )

        # Mejora de textos con IA
        context = f"Módulo: {module} - {title}"  # Usar parámetros recibidos
        enhanced_given = self._ai_enhance_step(given, context)
        enhanced_when = self._ai_enhance_step(when, context)
        enhanced_then = self._ai_enhance_step(then, context)

        return {
            'Given': enhanced_given[:120],
            'When': enhanced_when[:100],
            'Then': enhanced_then[:150],
            'And': [self._ai_enhance_step(a, context)[:100] 
                   for a in (when_candidates[1:] + then_candidates[:-1])[:2]]
        }

    
    def _create_action_summary(self, steps: list) -> list:
        """Resumen ejecutivo para automatización (requerido por _process_steps)"""
        action_map = {
            r'clic|seleccionar|presionar': 'Interactuar con elemento',
            r'capturar|ingresar': 'Capturar datos requeridos',
            r'validar|verificar': 'Validar información del sistema',
            r'habilitar|desplegar': 'Habilitar sección del formulario'
        }
        
        unique_actions = []
        for step in steps:
            for pattern, action in action_map.items():
                if re.search(pattern, step, re.IGNORECASE) and action not in unique_actions:
                    unique_actions.append(action)
                    break
        
        return unique_actions[:3]  # Máximo 3 acciones únicas

    def _format_step(self, text: str) -> str:
        """Formateo profesional para steps de automatización"""
        return '\n      '.join(textwrap.wrap(text, width=150, break_long_words=False))

    def _generate_feature(self, module: str, title: str, steps: Dict) -> str:
        """Generación de feature bulletproof"""
        # Limpieza de nombres
        clean_module = re.sub(r'\W+', '_', module.split('-')[-1]).strip('_')
        scenario_name = re.sub(r'[\W_]+', ' ', title.split('_')[-1]).title()[:70]
        
        feature_lines = [
            f"Feature: {clean_module}\n",
            f"  Scenario: {scenario_name}",
            f"    Given {self._format_step(steps['Given'])}"
        ]

        # When y And
        feature_lines.append(f"    When {self._format_step(steps['When'])}")
        for and_step in steps['And']:
            feature_lines.append(f"    And {self._format_step(and_step)}")

        # Then
        feature_lines.append(f"    Then {self._format_step(steps['Then'])}")
        
        return '\n'.join(feature_lines)

    def _normalize_filename(self, filename: str) -> str:
        """Normaliza el nombre del archivo eliminando caracteres especiales"""
        # Remover extensión .json
        name = filename.rsplit('.json', 1)[0]
        
        # Eliminar acentos y caracteres diacríticos
        normalized = unicodedata.normalize('NFKD', name)
        ascii_name = normalized.encode('ASCII', 'ignore').decode('utf-8')
        
        # Eliminar caracteres no permitidos
        cleaned = re.sub(r'[^\w\s-]', '', ascii_name)
        
        # Reemplazar espacios y guiones por _
        underscored = re.sub(r'[\s-]+', '_', cleaned)
        
        # Eliminar puntos restantes y dobles guiones bajos
        final_name = re.sub(r'[._]+', '_', underscored).strip('_')
        
        return f"{final_name}.feature"

    def convert(self):
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        for filename in os.listdir(self.input_dir):
            if filename.endswith('.json'):
                print(f"Procesando archivo: {filename}")
                try:
                    file_path = os.path.join(self.input_dir, filename)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Procesamiento mejorado con IA
                    processed = self._process_steps(
                        data.get("CasoPrueba", {}),
                        module=data.get("Modulo", "Modulo_Principal"),  # Nuevo parámetro de contexto
                        title=data.get("Titulo", "Escenario_Principal")
                    )
                    
                    feature_content = self._generate_feature(
                        module=data.get("Modulo", "Modulo_Principal"),
                        title=data.get("Titulo", "Escenario_Principal"),
                        steps=processed
                    )

                    feature_filename = self._normalize_filename(filename)
                    output_file = os.path.join(self.output_dir, feature_filename)
                    
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(feature_content)
                    print(f"Archivo generado: {output_file}")

                except json.JSONDecodeError as e:
                    print(f"Error en formato JSON: {filename} - {str(e)}")
                except Exception as e:
                    print(f"Error crítico procesando {filename}: {str(e)}")

if __name__ == "__main__":
    converter = UltimateGherkinConverterAI(
        input_dir="test_cases",
        output_dir="features"
    )
    converter.convert()