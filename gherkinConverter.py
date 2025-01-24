import json
import os
import re
import textwrap
import time
from typing import Dict, Any
import unicodedata


class UltimateGherkinConverter:
    def __init__(self, input_dir: str, output_dir: str):
        self.input_dir = input_dir
        self.output_dir = output_dir
        
    print("Inicializando IA...")  
    time.sleep(2)

    def _clean_text(self, text: str) -> str:
        """Limpieza avanzada manteniendo estructura clave"""
        return re.sub(r'[^\wá-úÁ-Ú \n\-]', '', text, flags=re.IGNORECASE).strip()

    def _is_valid_step(self, text: str) -> bool:
        """Validación mejorada de contenido"""
        return len(text) > 2 and not re.match(r'^[\d\W]+$', text)

    def _create_action_summary(self, steps: list) -> list:
        """Resumen ejecutivo para automatización"""
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

    def _process_steps(self, raw_steps: Dict) -> Dict[str, Any]:
        """Procesamiento ultra-robusto de pasos"""
        try:
            sorted_steps = sorted(
                ({'key': int(k), **v} for k, v in raw_steps.items()),
                key=lambda x: x['key']
            )
        except:
            sorted_steps = list(raw_steps.values())

        # Manejo de casos extremos
        if not sorted_steps:
            return {
                'Given': 'Iniciar flujo',
                'When': 'Ejecutar proceso',
                'Then': 'Proceso finalizado exitosamente',
                'And': []
            }

        # Given: Primer paso no vacío
        given = next(
            (f"Iniciar proceso: {self._clean_text(s['paso'])}" 
             for s in sorted_steps if s.get('paso')), 
            "Iniciar flujo"
        )

        # When: Resumen de acciones principales
        intermediate = [
            self._clean_text(s['paso']) 
            for s in sorted_steps[1:-1] 
            if s.get('paso') and self._is_valid_step(s['paso'])
        ]
        when_actions = self._create_action_summary(intermediate) or ['Ejecutar secuencia de pasos']
        when = when_actions[0]
        and_steps = when_actions[1:]  # Máximo 2 And

        # Then: Última validación significativa
        last_validation = next(
            (self._clean_text(s.get('validacion', '')) 
             for s in reversed(sorted_steps) 
             if self._is_valid_step(s.get('validacion', ''))),
            'Proceso finalizado exitosamente'
        )

        return {
            'Given': given[:120],  # Limitar longitud
            'When': when[:100],
            'Then': last_validation[:150],
            'And': [a[:100] for a in and_steps]
        }

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
                    
                    processed = self._process_steps(data.get("CasoPrueba", {}))
                    feature_content = self._generate_feature(
                        module=data.get("Modulo", "Modulo_Principal"),
                        title=data.get("Titulo", "Escenario_Principal"),
                        steps=processed
                    )

                    # Usar el método de normalización
                    feature_filename = self._normalize_filename(filename)
                    output_file = os.path.join(self.output_dir, feature_filename)
                    
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(feature_content)
                    print(f"Archivo generado: {output_file}")    

                except Exception as e:
                    print(f"Error procesando {filename}: {str(e)}")

if __name__ == "__main__":
    converter = UltimateGherkinConverter(
        input_dir="test_cases",
        output_dir="features"
    )
    converter.convert()