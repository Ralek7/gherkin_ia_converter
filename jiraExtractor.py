import json
import requests
import logging
import configparser
from base64 import b64encode
from typing import Dict, Optional, List
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class JiraExtractor:
    def __init__(self, url: str, email: str, api_token: str):
        """
        Inicializar el extractor de Jira

        Args:
            url: URL base de Jira (ej: https://coppelmx.atlassian.net)
            email: Correo registrado en Atlassian
            api_token: Token de API generado en Atlassian
        """
        self.url = url.rstrip('/')
        self.email = email
        self.api_token = api_token
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)
        self.auth_header = self._get_auth_header()

    def _get_auth_header(self) -> str:
        """Generar encabezado de autenticación Basic"""
        credentials = f"{self.email}:{self.api_token}"
        encoded_credentials = b64encode(credentials.encode('utf-8')).decode('utf-8')
        return f"Basic {encoded_credentials}"

    def check_connection(self) -> bool:
        """Verificar conexión y autenticación con Jira"""
        try:
            user_url = f"{self.url}/rest/api/3/myself"
            headers = {"Authorization": self.auth_header}
            
            self.logger.info("Verificando conexión a Jira...")
            response = self.session.get(user_url, headers=headers)
            
            if response.status_code == 200:
                user_data = response.json()
                self.logger.info(f"Conexión exitosa. Usuario: {user_data.get('displayName')}")
                return True
            
            self.logger.error(f"Error de autenticación. Código: {response.status_code}")
            self.logger.error(f"Respuesta: {response.text}")
            return False

        except Exception as e:
            self.logger.error(f"Error de conexión: {str(e)}")
            return False

    def get_user_permissions(self) -> Dict:
        """Obtener permisos del usuario autenticado"""
        try:
            permissions_url = f"{self.url}/rest/api/3/mypermissions"
            headers = {"Authorization": self.auth_header}
            params = {"permissions": "BROWSE_PROJECTS,VIEW_ISSUES"}  # Permisos específicos
            
            response = self.session.get(
                permissions_url,
                headers=headers,
                params=params
            )
            
            if response.status_code == 200:
                return response.json()
            
            self.logger.error(f"Error al obtener permisos: {response.text}")
            return {}

        except Exception as e:
            self.logger.error(f"Error: {str(e)}")
            return {}

    def get_issue(self, issue_id: str) -> Optional[Dict]:
        """Obtener un issue específico"""
        try:
            issue_url = f"{self.url}/rest/api/3/issue/{issue_id}"
            headers = {"Authorization": self.auth_header}
            
            self.logger.info(f"Obteniendo issue {issue_id}...")
            response = self.session.get(issue_url, headers=headers)
            
            if response.status_code == 200:
                return response.json()
            
            self.logger.error(f"Error obteniendo issue: {response.text}")
            return None

        except Exception as e:
            self.logger.error(f"Error: {str(e)}")
            return None

    def get_all_issues(self, project_key: str) -> Optional[List[str]]:
        """Obtener todos los issues de un proyecto"""
        try:
            issues = []
            start_at = 0
            max_results = 100
            
            while True:
                params = {
                    "jql": f"project = {project_key}",
                    "startAt": start_at,
                    "maxResults": max_results,
                    "fields": "key"
                }
                
                response = self.session.get(
                    f"{self.url}/rest/api/3/search",
                    headers={"Authorization": self.auth_header},
                    params=params
                )
                
                if response.status_code != 200:
                    self.logger.error(f"Error: {response.text}")
                    return None
                
                data = response.json()
                issues.extend([issue["key"] for issue in data.get("issues", [])])
                
                if data.get("total") <= start_at + max_results:
                    break
                    
                start_at += max_results
            
            return issues

        except Exception as e:
            self.logger.error(f"Error: {str(e)}")
            return None

    def save_issue(self, issue: Dict, output_dir: str = "jira_issues") -> None:
        """Guardar issue en formato JSON"""
        try:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            issue_key = issue.get("key", "unknown_issue")
            
            with open(Path(output_dir) / f"{issue_key}.json", "w", encoding="utf-8") as f:
                json.dump(issue, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Issue {issue_key} guardado")

        except Exception as e:
            self.logger.error(f"Error guardando archivo: {str(e)}")

def main():
    """Interfaz principal de ejecución"""
    try:
        # Leer configuración desde secrets.ini
        config = configparser.ConfigParser()
        config.read('secrets\secrets.ini', encoding='utf-8')
        
        # Obtener valores de JIRA
        jira_url = config.get('JIRA', 'URL')
        email = config.get('JIRA', 'EMAIL')
        api_token = config.get('JIRA', 'API_TOKEN')

        # Inicializar extractor
        extractor = JiraExtractor(jira_url, email, api_token)
        
        # Verificar conexión
        if not extractor.check_connection():
            print("\n❌ Error de autenticación. Verifica token y credenciales")
            return

        # Pedir clave del proyecto primero
        project_key = input("\nClave del proyecto (ej: BT115): ").strip()

        # Menú interactivo
        print("\n=== Jira Extractor ===")
        option = input(
            "Selecciona una opción:\n"
            "1. Extraer un issue específico de este proyecto\n"
            "2. Extraer todos los issues del proyecto\n"
            "Opción: "
        )

        if option == "1":
            issue_number = input("Número del issue (ej: 123): ").strip()
            issue_id = f"{project_key}-{issue_number}"
            if issue := extractor.get_issue(issue_id):
                extractor.save_issue(issue)
                print(f"\n✅ Issue {issue_id} guardado exitosamente!")
            else:
                print("\n❌ No se pudo obtener el issue")

        elif option == "2":
            if issues := extractor.get_all_issues(project_key):
                print(f"\n🔍 Encontrados {len(issues)} issues en {project_key}")
                for issue_id in issues:
                    if issue := extractor.get_issue(issue_id):
                        extractor.save_issue(issue)
                        print(f"✔ {issue_id} procesado")
                print("\n✅ Extracción completada!")
            else:
                print("\n❌ Error al obtener issues")

        else:
            print("\n⚠ Opción no válida")

    except Exception as e:
        print(f"\n🔥 Error crítico: {str(e)}")

if __name__ == "__main__":
    main()