import requests
from base64 import b64encode

# Configuración
jira_url = "https://coppelmx.atlassian.net"
email = "jasanchezs@bancoppel.com"
api_token = "ATATT3xFfGF0Ui4tAtOqUCCxidCX9OLaUVWibusNHzBar5RN_8DHJo6RpSCkKuygw5DzytdWBf4UvikSmtT4JCXEZktUcs0WSmCBdR6U05X5WKYQaS3REIyDSgs6EtenQSME_8hSDRf3mhN30YBx7OW4HxN2XbpCraMIUmJVN_HOpD2LHQt-uHw=FF348170"  # ¡Pega el nuevo token generado!

# Generar encabezado de autenticación
credentials = f"{email}:{api_token}"
encoded_credentials = b64encode(credentials.encode("utf-8")).decode("utf-8")
auth_header = f"Basic {encoded_credentials}"

# Realizar solicitud de prueba
try:
    response = requests.get(
        f"{jira_url}/rest/api/3/myself",
        headers={"Authorization": auth_header}
    )
    
    print("=== Depuración ===")
    print(f"URL: {jira_url}/rest/api/3/myself")
    print(f"Encabezado de autenticación: {auth_header}")
    print(f"Código de respuesta: {response.status_code}")
    print(f"Respuesta: {response.text}")

    if response.status_code == 200:
        print("\n✅ ¡Autenticación exitosa!")
        print(f"Usuario: {response.json().get('displayName')}")
    else:
        print("\n❌ Error 401: Verifica el token y el correo electrónico.")

except Exception as e:
    print(f"\n🔥 Error crítico: {str(e)}")