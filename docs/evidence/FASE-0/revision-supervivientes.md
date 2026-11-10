# Revisión individual de supervivientes

Cada fila corresponde a un mutante inspeccionado mediante el diff AST guardado en el paquete. Las equivalencias se limitan a las plataformas y formatos soportados. El umbral conserva el denominador completo.

| Mutante | Clasificación | Justificación |
|---|---|---|
| `_changed__mutmut_23` | Justificado | Alias de códec UTF-8/LATIN-1 o cambio de docstring, sin cambio de decodificación. |
| `_decode__mutmut_1` | Justificado | Alias de códec UTF-8/LATIN-1 o cambio de docstring, sin cambio de decodificación. |
| `_decode__mutmut_12` | Justificado | Alias de códec UTF-8/LATIN-1 o cambio de docstring, sin cambio de decodificación. |
| `_decode__mutmut_9` | Justificado | Alias de códec UTF-8/LATIN-1 o cambio de docstring, sin cambio de decodificación. |
| `_enclosing_identifier__mutmut_3` | Justificado | Cuando el término comienza con el identificador, el fragmento alternativo coincide con el identificador completo consumido por el patrón. |
| `_git__mutmut_8` | Justificado | Equivalencia en APFS sin distinción de mayúsculas. En sistemas sensibles, el mutante rechaza por fallo de Git. El original conserva git y HEAD canónicos. |
| `_glob_hits_secret__mutmut_2` | Justificado | El mutante amplía la evaluación de tokens. La comparación fnmatch y la detección literal de rutas mantienen el bloqueo efectivo. |
| `_glob_hits_secret__mutmut_3` | Justificado | El mutante amplía la evaluación de tokens. La comparación fnmatch y la detección literal de rutas mantienen el bloqueo efectivo. |
| `_settings_without_deny__mutmut_12` | Justificado | Solo cambia la serialización o ensure_ascii=None equivalente a False. La sensibilidad JSON se comprueba por estructura. Puede variar el número de línea del diagnóstico. |
| `_settings_without_deny__mutmut_13` | Justificado | Solo cambia la serialización o ensure_ascii=None equivalente a False. La sensibilidad JSON se comprueba por estructura. Puede variar el número de línea del diagnóstico. |
| `_settings_without_deny__mutmut_15` | Justificado | Solo cambia la serialización o ensure_ascii=None equivalente a False. La sensibilidad JSON se comprueba por estructura. Puede variar el número de línea del diagnóstico. |
| `_settings_without_deny__mutmut_17` | Justificado | Solo cambia la serialización o ensure_ascii=None equivalente a False. La sensibilidad JSON se comprueba por estructura. Puede variar el número de línea del diagnóstico. |
| `check_file__mutmut_129` | Justificado | Sustitución del comentario por texto sin anotación, o condición redundante de JSON. JSON válido usa la ruta estructural. La prueba YAML elimina la inversión insegura de la condición. |
| `check_file__mutmut_131` | Justificado | Sustitución del comentario por texto sin anotación, o condición redundante de JSON. JSON válido usa la ruta estructural. La prueba YAML elimina la inversión insegura de la condición. |
| `check_file__mutmut_132` | Justificado | Sustitución del comentario por texto sin anotación, o condición redundante de JSON. JSON válido usa la ruta estructural. La prueba YAML elimina la inversión insegura de la condición. |
| `check_file__mutmut_138` | Justificado | Variar el límite de split conserva el primer elemento seleccionado. |
| `check_file__mutmut_143` | Justificado | Variar el límite de split conserva el primer elemento seleccionado. |
| `check_file__mutmut_146` | Justificado | Variar el límite de split conserva el primer elemento seleccionado. |
| `check_file__mutmut_149` | Justificado | Variar el límite de split conserva el primer elemento seleccionado. |
| `check_file__mutmut_26` | Justificado | UTF-8 y UTF-8 en mayúsculas designan el mismo códec. |
| `check_file__mutmut_32` | Justificado | Todas las firmas de audio consultadas terminan antes del byte 16. Añadir un byte al prefijo no cambia la decisión. |
| `check_file__mutmut_79` | Justificado | None y False son falsos en la condición is_schema posterior. |
| `load_allowlist__mutmut_10` | Justificado | Primer elemento de split idéntico, o códec UTF-8 explícito/por defecto en las plataformas soportadas. |
| `load_allowlist__mutmut_13` | Justificado | Primer elemento de split idéntico, o códec UTF-8 explícito/por defecto en las plataformas soportadas. |
| `load_allowlist__mutmut_3` | Justificado | Primer elemento de split idéntico, o códec UTF-8 explícito/por defecto en las plataformas soportadas. |
| `load_allowlist__mutmut_5` | Justificado | Primer elemento de split idéntico, o códec UTF-8 explícito/por defecto en las plataformas soportadas. |
| `main__mutmut_16` | Justificado | Texto de ayuda/error sin cambiar el rechazo, o carga de la misma lista por el valor por defecto de check_file. |
| `main__mutmut_18` | Justificado | Texto de ayuda/error sin cambiar el rechazo, o carga de la misma lista por el valor por defecto de check_file. |
| `main__mutmut_2` | Justificado | Texto de ayuda/error sin cambiar el rechazo, o carga de la misma lista por el valor por defecto de check_file. |
| `main__mutmut_21` | Justificado | Texto de ayuda/error sin cambiar el rechazo, o carga de la misma lista por el valor por defecto de check_file. |
| `main__mutmut_22` | Justificado | Texto de ayuda/error sin cambiar el rechazo, o carga de la misma lista por el valor por defecto de check_file. |
| `main__mutmut_3` | Justificado | Texto de ayuda/error sin cambiar el rechazo, o carga de la misma lista por el valor por defecto de check_file. |
| `main__mutmut_39` | Justificado | Texto de ayuda/error sin cambiar el rechazo, o carga de la misma lista por el valor por defecto de check_file. |
| `main__mutmut_40` | Justificado | Texto de ayuda/error sin cambiar el rechazo, o carga de la misma lista por el valor por defecto de check_file. |
| `main__mutmut_41` | Justificado | Texto de ayuda/error sin cambiar el rechazo, o carga de la misma lista por el valor por defecto de check_file. |
| `main__mutmut_42` | Justificado | Texto de ayuda/error sin cambiar el rechazo, o carga de la misma lista por el valor por defecto de check_file. |
| `main__mutmut_51` | Justificado | Texto de ayuda/error sin cambiar el rechazo, o carga de la misma lista por el valor por defecto de check_file. |
| `main__mutmut_55` | Justificado | Texto de ayuda/error sin cambiar el rechazo, o carga de la misma lista por el valor por defecto de check_file. |
| `main__mutmut_58` | Justificado | Texto de ayuda/error sin cambiar el rechazo, o carga de la misma lista por el valor por defecto de check_file. |
| `range_files__mutmut_12` | Justificado | Equivalencia en APFS sin distinción de mayúsculas. En sistemas sensibles, el mutante rechaza por fallo de Git. El original conserva git y HEAD canónicos. |
| `range_files__mutmut_9` | Justificado | El rango admitido tiene dos extremos. Índices +1 y -1 seleccionan el mismo extremo final. |

El timeout _json_pilot_fields__mutmut_4 sustituye pop por None y deja la cola sin consumir. Se registra como timeout y se mantiene fuera del numerador.

Las pruebas nuevas eliminaron supervivientes reales de límites binarios, comentarios YAML, escapes de shell, aislamiento de campos y diagnóstico JSON. Esta revisión retira la clasificación histórica general y conserva las diferencias de disponibilidad/diagnóstico expresamente descritas.
