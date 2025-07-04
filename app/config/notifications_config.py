

import os
from typing import Dict, Any

# Configuración de Google OAuth
GOOGLE_OAUTH_CONFIG = {
    "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
    "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
    "scopes": [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.send'
    ],
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth"
}

# Configuración de Gmail
GMAIL_CONFIG = {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "email_query": 'subject:"Factura Digital"',
    "max_emails_per_check": 50,
    "rate_limit_delay": 1  # segundos entre requests
}

# Configuración de detección de anomalías
ANOMALY_CONFIG = {
    "min_score_threshold": -0.5,  # Score mínimo para considerar anomalía
    "min_increase_percentage": 20,  # Aumento mínimo % para alertar
    "contamination_rate": 0.1,  # Tasa de contaminación para IsolationForest
    "min_historical_data": 3,  # Mínimo de datos históricos para comparar
    "alert_cooldown_hours": 24  # Horas entre alertas para el mismo NIC
}

# Configuración de monitoreo automático
MONITORING_CONFIG = {
    "default_interval_hours": 2,  # Intervalo por defecto entre monitoreos
    "min_interval_hours": 0.5,  # Intervalo mínimo permitido
    "max_interval_hours": 24,  # Intervalo máximo permitido
    "max_concurrent_users": 10,  # Máximo de usuarios procesando simultáneamente
    "timeout_per_user_seconds": 300  # Timeout por usuario
}

# Configuración de logging
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": "logs/notifications.log",
    "max_file_size": 10 * 1024 * 1024,  # 10MB
    "backup_count": 5
}

# Plantillas de email
EMAIL_TEMPLATES = {
    "anomaly_alert": {
        "subject_template": "🚨 Alerta: Consumo Eléctrico Alto Detectado - {anomaly_count} Anomalía(s)",
        "max_anomalies_in_email": 10,  # Máximo de anomalías en un email
        "include_charts": False,  # Incluir gráficos (futuro)
        "include_recommendations": True
    }
}

# Configuración de límites de API
API_LIMITS = {
    "gmail_requests_per_minute": 100,
    "gmail_requests_per_day": 1000000,
    "max_retries": 3,
    "retry_delay_seconds": 5
}

def get_config() -> Dict[str, Any]:
    """
    Obtener toda la configuración del servicio
    
    Returns:
        Diccionario con toda la configuración
    """
    return {
        "google_oauth": GOOGLE_OAUTH_CONFIG,
        "gmail": GMAIL_CONFIG,
        "anomaly": ANOMALY_CONFIG,
        "monitoring": MONITORING_CONFIG,
        "logging": LOGGING_CONFIG,
        "email_templates": EMAIL_TEMPLATES,
        "api_limits": API_LIMITS
    }

def validate_config() -> Dict[str, Any]:
    """
    Validar la configuración del servicio
    
    Returns:
        Resultado de la validación
    """
    issues = []
    warnings = []
    
    # Verificar variables de entorno críticas
    if not GOOGLE_OAUTH_CONFIG["client_id"]:
        issues.append("GOOGLE_CLIENT_ID no configurado")
    
    if not GOOGLE_OAUTH_CONFIG["client_secret"]:
        issues.append("GOOGLE_CLIENT_SECRET no configurado")
    
    # Verificar configuración de anomalías
    if ANOMALY_CONFIG["min_score_threshold"] > 0:
        warnings.append("min_score_threshold debería ser negativo para IsolationForest")
    
    if ANOMALY_CONFIG["min_increase_percentage"] < 10:
        warnings.append("min_increase_percentage muy bajo, puede generar muchas alertas falsas")
    
    # Verificar configuración de monitoreo
    if MONITORING_CONFIG["default_interval_hours"] < 1:
        warnings.append("Intervalo de monitoreo muy frecuente, puede agotar límites de API")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "total_issues": len(issues),
        "total_warnings": len(warnings)
    }

def get_environment_info() -> Dict[str, Any]:
    """
    Obtener información del entorno
    
    Returns:
        Información del entorno y configuración
    """
    return {
        "config_loaded": True,
        "google_client_id_configured": bool(GOOGLE_OAUTH_CONFIG["client_id"]),
        "google_client_secret_configured": bool(GOOGLE_OAUTH_CONFIG["client_secret"]),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "debug_mode": os.getenv("DEBUG", "false").lower() == "true",
        "validation": validate_config()
    }
