import requests
from base64 import b64encode

# Configuración
jira_url = "https://coppelmx.atlassian.net"
email = "jasanchezs@bancoppel.com"
api_token = "ATATT3xFfGF0r7Ymbhc7NoGBUmzaw5mm9v_oTpAzdx47fRpWdq2IN4-a4G4pUcdUNh4uavmmibZx4zyQ1ZKmKyLmQiUy6FbH_tok6ZbBs_k3G7vZ15fF5RpURZ1qrta0-1f_mmIBvGNbgUTN37wAS95aoZS8g-bEl8zgyREoNYnzvp6xSN38xl8=CE16FD39" 

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