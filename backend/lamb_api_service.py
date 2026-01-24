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
        url = f"{LAMBAPIService.LAMB_API_URL}/v1/models"
        logging.info(f"Verificando modelo LAMB en: {url}")
        
        try:
            response = requests.get(url, timeout=10)
            
            logging.info(f"LAMB /v1/models response status: {response.status_code}")
            logging.debug(f"LAMB /v1/models response headers: {dict(response.headers)}")
            
            if response.status_code != 200:
                error_detail = ""
                try:
                    error_detail = f" - Respuesta: {response.text[:500]}" if response.text else ""
                except:
                    pass
                return {
                    "success": False,
                    "error": f"Error al conectar con el servidor LAMB (código {response.status_code}){error_detail}"
                }
            
            # Log raw response for debugging
            raw_text = response.text
            logging.debug(f"LAMB /v1/models raw response (first 500 chars): {raw_text[:500] if raw_text else '(empty)'}")
            
            if not raw_text or not raw_text.strip():
                return {
                    "success": False,
                    "error": f"El servidor LAMB retornó una respuesta vacía. URL: {url}"
                }
            
            try:
                data = response.json()
            except Exception as json_err:
                logging.error(f"Error parseando JSON de LAMB: {json_err}. Respuesta raw: {raw_text[:500]}")
                return {
                    "success": False,
                    "error": f"El servidor LAMB retornó una respuesta no válida (no es JSON). Respuesta: {raw_text[:200]}"
                }
            
            models = data.get("data", [])
            model_id = f"lamb_assistant.{evaluator_id}"
            
            logging.info(f"Buscando modelo '{model_id}' entre {len(models)} modelos disponibles")
            logging.debug(f"Modelos disponibles: {[m.get('id') for m in models]}")
            
            model_found = any(model.get("id") == model_id for model in models)
            
            if model_found:
                return {
                    "success": True,
                    "model_id": model_id,
                    "message": f"Modelo {model_id} encontrado correctamente"
                }
            else:
                available_models = [m.get('id') for m in models[:10]]  # Show first 10
                return {
                    "success": False,
                    "error": f"No se encontró el modelo '{model_id}' en el servidor LAMB. Modelos disponibles: {available_models}"
                }
                
        except requests.exceptions.Timeout:
            return {"success": False, "error": f"Tiempo de espera agotado al conectar con el servidor LAMB ({url})"}
        except requests.exceptions.ConnectionError as e:
            return {"success": False, "error": f"No se pudo conectar con el servidor LAMB ({url}): {str(e)}"}
        except Exception as e:
            logging.exception(f"Error inesperado al verificar modelo LAMB")
            return {"success": False, "error": f"Error al verificar el modelo LAMB: {type(e).__name__}: {str(e)}"}
    
    @staticmethod
    def evaluate_text(text: str, evaluator_id: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """Envía texto al modelo LAMB para evaluación"""
        model_id = f"lamb_assistant.{evaluator_id}"
        url = f"{LAMBAPIService.LAMB_API_URL}/chat/completions"
        effective_timeout = timeout or LAMBAPIService.LAMB_TIMEOUT
        
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f"Bearer {LAMBAPIService.LAMB_BEARER_TOKEN}"
            }
            payload = {'model': model_id, 'prompt': text}
            
            logging.info(f"Enviando solicitud de evaluación al modelo LAMB {model_id}")
            logging.info(f"URL: {url}, Timeout: {effective_timeout}s, Text length: {len(text)} chars")
            logging.debug(f"Headers: {headers}")
            logging.debug(f"Payload model: {payload['model']}, prompt length: {len(payload['prompt'])}")
            
            response = requests.post(url, headers=headers, json=payload, timeout=effective_timeout)
            
            logging.info(f"LAMB /chat/completions response status: {response.status_code}")
            
            if response.status_code != 200:
                raw_text = response.text[:500] if response.text else "(empty)"
                error_msg = f"LAMB API retornó status {response.status_code}"
                try:
                    error_detail = response.json()
                    error_msg += f": {error_detail}"
                except:
                    error_msg += f": {raw_text}"
                logging.error(error_msg)
                return {'success': False, 'error': error_msg}
            
            # Check for empty response
            raw_text = response.text
            if not raw_text or not raw_text.strip():
                error_msg = f"LAMB API retornó una respuesta vacía (status 200). URL: {url}"
                logging.error(error_msg)
                return {'success': False, 'error': error_msg}
            
            # Try to parse JSON
            try:
                response_json = response.json()
            except Exception as json_err:
                error_msg = f"LAMB API retornó respuesta no válida (no es JSON): {raw_text[:300]}"
                logging.error(error_msg)
                return {'success': False, 'error': error_msg}
            
            logging.info("Respuesta de evaluación recibida de LAMB")
            logging.debug(f"Response keys: {response_json.keys() if isinstance(response_json, dict) else type(response_json)}")
            
            return {'success': True, 'response': response_json, 'model_id': model_id}
            
        except requests.exceptions.Timeout:
            error_msg = f"Timeout al conectar con LAMB API (> {effective_timeout}s). URL: {url}"
            logging.error(error_msg)
            return {'success': False, 'error': error_msg}
        except requests.exceptions.ConnectionError as e:
            error_msg = f"No se pudo conectar con LAMB API ({url}): {str(e)}"
            logging.error(error_msg)
            return {'success': False, 'error': error_msg}
        except Exception as e:
            error_msg = f"Error inesperado al llamar a LAMB API: {type(e).__name__}: {str(e)}"
            logging.exception(error_msg)
            return {'success': False, 'error': error_msg}
    
    @staticmethod
    def validate_chat_completions_format(response: Dict[str, Any]) -> Dict[str, Any]:
        """Validates that the response follows the expected chat completions format.
        
        Expected format (OpenAI-compatible):
        {
            "choices": [
                {
                    "message": {
                        "content": "..."
                    }
                }
            ]
        }
        
        Returns validation results with details about any issues found.
        """
        validation = {
            'is_valid': True,
            'format_detected': None,
            'issues': [],
            'structure': {}
        }
        
        if not isinstance(response, dict):
            validation['is_valid'] = False
            validation['issues'].append(f"Response is not a dict, got: {type(response).__name__}")
            return validation
        
        validation['structure']['top_level_keys'] = list(response.keys())
        
        # Check for OpenAI chat completions format
        if 'choices' in response:
            validation['format_detected'] = 'openai_chat_completions'
            choices = response.get('choices', [])
            
            if not isinstance(choices, list):
                validation['is_valid'] = False
                validation['issues'].append(f"'choices' is not a list, got: {type(choices).__name__}")
            elif len(choices) == 0:
                validation['is_valid'] = False
                validation['issues'].append("'choices' array is empty")
            else:
                choice = choices[0]
                validation['structure']['first_choice_keys'] = list(choice.keys()) if isinstance(choice, dict) else None
                
                if not isinstance(choice, dict):
                    validation['is_valid'] = False
                    validation['issues'].append(f"First choice is not a dict, got: {type(choice).__name__}")
                elif 'message' in choice:
                    message = choice.get('message', {})
                    validation['structure']['message_keys'] = list(message.keys()) if isinstance(message, dict) else None
                    
                    if not isinstance(message, dict):
                        validation['is_valid'] = False
                        validation['issues'].append(f"'message' is not a dict, got: {type(message).__name__}")
                    elif 'content' not in message:
                        validation['is_valid'] = False
                        validation['issues'].append("'message' does not contain 'content' key")
                    elif not isinstance(message.get('content'), str):
                        validation['issues'].append(f"'content' is not a string, got: {type(message.get('content')).__name__}")
                elif 'text' in choice:
                    validation['format_detected'] = 'openai_completions_legacy'
                    if not isinstance(choice.get('text'), str):
                        validation['issues'].append(f"'text' is not a string, got: {type(choice.get('text')).__name__}")
                else:
                    validation['is_valid'] = False
                    validation['issues'].append("First choice has neither 'message' nor 'text' key")
        
        # Check for alternative formats
        elif 'content' in response:
            validation['format_detected'] = 'simple_content'
            if not isinstance(response.get('content'), str):
                validation['issues'].append(f"'content' is not a string, got: {type(response.get('content')).__name__}")
        elif 'text' in response:
            validation['format_detected'] = 'simple_text'
            if not isinstance(response.get('text'), str):
                validation['issues'].append(f"'text' is not a string, got: {type(response.get('text')).__name__}")
        else:
            validation['is_valid'] = False
            validation['format_detected'] = 'unknown'
            validation['issues'].append("Response doesn't match any known format (missing 'choices', 'content', or 'text')")
        
        return validation
    
    @staticmethod
    def parse_evaluation_response(response: Dict[str, Any]) -> Dict[str, Any]:
        """Parsea la respuesta de LAMB API para extraer nota y feedback"""
        try:
            logging.info(f"=== PARSING LAMB RESPONSE ===")
            logging.info(f"Response type: {type(response)}")
            logging.info(f"Response keys: {response.keys() if isinstance(response, dict) else 'N/A'}")
            logging.info(f"Full response: {response}")
            
            # Check if the LAMB API call itself failed
            if isinstance(response, dict) and response.get('success') == False:
                error_msg = response.get('error', 'Unknown LAMB API error')
                logging.error(f"LAMB API returned error: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'score': None,
                    'comment': None,
                    'raw_response': response
                }
            
            # First validate the response format
            validation = LAMBAPIService.validate_chat_completions_format(response)
            logging.info(f"Validation result: {validation}")
            
            content = None
            
            # Try to extract content from various response formats
            if 'response' in response and isinstance(response['response'], dict):
                # Handle wrapped response from evaluate_text
                inner_response = response['response']
                logging.info(f"Found inner 'response' key, extracting from it")
                if 'choices' in inner_response and len(inner_response['choices']) > 0:
                    choice = inner_response['choices'][0]
                    content = choice.get('message', {}).get('content') or choice.get('text')
                    logging.info(f"Extracted content from inner response choices: {content[:200] if content else 'None'}...")
            
            if not content and 'choices' in response and len(response['choices']) > 0:
                choice = response['choices'][0]
                content = choice.get('message', {}).get('content') or choice.get('text')
                logging.info(f"Extracted content from choices: {content[:200] if content else 'None'}...")
            elif not content and 'content' in response:
                content = response['content']
                logging.info(f"Extracted content from 'content' key: {content[:200] if content else 'None'}...")
            elif not content and 'text' in response:
                content = response['text']
                logging.info(f"Extracted content from 'text' key: {content[:200] if content else 'None'}...")
            
            if content:
                result = LAMBAPIService._extract_score_and_feedback(content)
                result['success'] = True
                result['json_validation'] = validation
                logging.info(f"Successfully parsed response. Score: {result.get('score')}")
                return result
            
            logging.warning(f"Could not extract content from response. Returning raw response.")
            return {
                'success': True,  # Not an error, just no structured content
                'score': None, 
                'comment': str(response), 
                'raw_response': response,
                'json_validation': validation
            }
                
        except Exception as e:
            logging.error(f"Error parseando respuesta LAMB: {str(e)}")
            logging.exception("Full traceback:")
            return {
                'success': False,
                'error': f"Error al procesar respuesta: {str(e)}",
                'score': None, 
                'comment': f"Error al procesar respuesta: {str(e)}", 
                'raw_response': response,
                'json_validation': {'is_valid': False, 'issues': [str(e)]}
            }
    
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

