"""
LAMB API Service - Comunica con la API de evaluación LAMB
"""
import os
import logging
import requests
import re
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

class LAMBAPIService:
    """Servicio para interactuar con la API LAMB"""
    
    LAMB_API_URL = os.getenv('LAMB_API_URL', 'http://lamb.lamb-project.org:9099')
    LAMB_BEARER_TOKEN = os.getenv('LAMB_BEARER_TOKEN', '0p3n-w3bu!-wasabi')
    LAMB_TIMEOUT = int(os.getenv('LAMB_TIMEOUT', '30'))
    
    @staticmethod
    def verify_model_exists(evaluator_id: str) -> Dict[str, Any]:
        """Verifica que existe un modelo LAMB con el evaluator_id dado"""
        try:
            response = requests.get(
                f"{LAMBAPIService.LAMB_API_URL}/v1/models",
                timeout=10
            )
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Error al conectar con el servidor LAMB (código {response.status_code})"
                }
            
            data = response.json()
            models = data.get("data", [])
            model_id = f"lamb_assistant.{evaluator_id}"
            model_found = any(model.get("id") == model_id for model in models)
            
            if model_found:
                return {
                    "success": True,
                    "model_id": model_id,
                    "message": f"Modelo {model_id} encontrado correctamente"
                }
            else:
                return {
                    "success": False,
                    "error": f"No se encontró el modelo '{model_id}' en el servidor LAMB"
                }
                
        except requests.exceptions.Timeout:
            return {"success": False, "error": "Tiempo de espera agotado al conectar con el servidor LAMB"}
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "No se pudo conectar con el servidor LAMB"}
        except Exception as e:
            return {"success": False, "error": f"Error al verificar el modelo LAMB: {str(e)}"}
    
    @staticmethod
    def evaluate_text(text: str, evaluator_id: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """Envía texto al modelo LAMB para evaluación"""
        try:
            model_id = f"lamb_assistant.{evaluator_id}"
            url = f"{LAMBAPIService.LAMB_API_URL}/chat/completions"
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f"Bearer {LAMBAPIService.LAMB_BEARER_TOKEN}"
            }
            payload = {'model': model_id, 'prompt': text}
            effective_timeout = timeout or LAMBAPIService.LAMB_TIMEOUT
            
            logging.info(f"Enviando solicitud de evaluación al modelo LAMB {model_id}")
            
            response = requests.post(url, headers=headers, json=payload, timeout=effective_timeout)
            
            if response.status_code != 200:
                error_msg = f"LAMB API retornó status {response.status_code}"
                try:
                    error_msg += f": {response.json()}"
                except:
                    error_msg += f": {response.text}"
                logging.error(error_msg)
                return {'success': False, 'error': error_msg}
            
            logging.info("Respuesta de evaluación recibida de LAMB")
            return {'success': True, 'response': response.json(), 'model_id': model_id}
            
        except requests.exceptions.Timeout:
            error_msg = f"Timeout al conectar con LAMB API (> {effective_timeout}s)"
            logging.error(error_msg)
            return {'success': False, 'error': error_msg}
        except requests.exceptions.ConnectionError:
            error_msg = "No se pudo conectar con LAMB API"
            logging.error(error_msg)
            return {'success': False, 'error': error_msg}
        except Exception as e:
            error_msg = f"Error inesperado al llamar a LAMB API: {str(e)}"
            logging.error(error_msg)
            return {'success': False, 'error': error_msg}
    
    @staticmethod
    def parse_evaluation_response(response: Dict[str, Any]) -> Dict[str, Any]:
        """Parsea la respuesta de LAMB API para extraer nota y feedback"""
        try:
            content = None
            
            if 'choices' in response and len(response['choices']) > 0:
                choice = response['choices'][0]
                content = choice.get('message', {}).get('content') or choice.get('text')
            elif 'content' in response:
                content = response['content']
            elif 'text' in response:
                content = response['text']
            
            if content:
                return LAMBAPIService._extract_score_and_feedback(content)
            
            return {'score': None, 'comment': str(response), 'raw_response': response}
                
        except Exception as e:
            logging.error(f"Error parseando respuesta LAMB: {str(e)}")
            return {'score': None, 'comment': f"Error al procesar respuesta: {str(e)}", 'raw_response': response}
    
    @staticmethod
    def _extract_score_and_feedback(content: str) -> Dict[str, Any]:
        """Extrae nota y feedback del contenido de texto
        
        Busca los formatos:
        - "NOTA FINAL: X.X"
        - "FINAL SCORE: X.X"
        """
        score = None
        
        # Buscar los patrones "NOTA FINAL: X.X" o "FINAL SCORE: X.X"
        pattern = r'(?:NOTA\s+FINAL|FINAL\s+SCORE)\s*:\s*(\d+\.?\d*)'
        match = re.search(pattern, content, re.IGNORECASE)
        
        if match:
            try:
                score = float(match.group(1))
                if 0 <= score <= 10:
                    logging.info(f"Nota extraída: {score}")
                else:
                    logging.warning(f"Nota fuera de rango (0-10): {score}")
                    score = None
            except (ValueError, IndexError) as e:
                logging.error(f"Error al convertir nota a float: {str(e)}")
                score = None
        
        # Si no se encuentra nota en el formato esperado, loguear una advertencia
        if score is None:
            logging.warning("No se encontró el formato 'NOTA FINAL: X.X' o 'FINAL SCORE: X.X' en la respuesta del agente LAMB")
        
        return {'score': score, 'comment': content, 'raw_response': content}

