# Guía del Analizador de Código

## 📋 Descripción

El analizador de código (`code_analyzer.py`) es una herramienta integral que utiliza **20 métodos de análisis** para revisar código Python línea por línea, identificando problemas de sintaxis, indentación, lógica y estilo.

## 🚀 Uso

### Análisis Básico

```bash
# Analizar el directorio actual
python code_analyzer.py

# Analizar un directorio específico
python code_analyzer.py /ruta/al/proyecto

# Analizar un archivo específico
python code_analyzer.py archivo.py
```

### Ejemplos de Uso

```bash
# Analizar todos los archivos del proyecto
python code_analyzer.py .

# Analizar solo el módulo de RAM
python code_analyzer.py ram.py

# Analizar con redirección a archivo
python code_analyzer.py . > analisis_completo.txt
```

## 🔍 Los 20 Métodos de Análisis

### 1. **Syntax Check** (Verificación de Sintaxis)
- **Detecta**: Errores de sintaxis de Python
- **Severidad**: CRITICAL
- **Ejemplo**: `if x = 5:` (debe ser `==`)

### 2. **Indentation Check** (Verificación de Indentación)
- **Detecta**: Mezcla de tabs y espacios, indentación incorrecta
- **Severidad**: ERROR/WARNING
- **Ejemplo**: Tabs mezclados con espacios

### 3. **Function Completeness** (Funciones Completas)
- **Detecta**: Funciones vacías o solo con `pass`
- **Severidad**: ERROR/INFO
- **Ejemplo**: 
```python
def get_stats(self):  # Función sin cuerpo
```

### 4. **Unreachable Code** (Código Inalcanzable)
- **Detecta**: Código después de return/raise
- **Severidad**: WARNING
- **Ejemplo**:
```python
def ejemplo():
    return True
    print("Nunca se ejecuta")  # ⚠️ Inalcanzable
```

### 5. **Undefined Variables** (Variables No Definidas)
- **Detecta**: Uso de variables antes de definirlas
- **Severidad**: WARNING
- **Ejemplo**: Uso de variable antes de asignación

### 6. **Unused Imports** (Importaciones Sin Usar)
- **Detecta**: Módulos importados pero no utilizados
- **Severidad**: INFO
- **Ejemplo**: `import sys` sin usar `sys`

### 7. **Line Length** (Longitud de Línea)
- **Detecta**: Líneas que exceden 120 caracteres
- **Severidad**: INFO
- **Ejemplo**: Línea de 150 caracteres

### 8. **Docstring Check** (Verificación de Documentación)
- **Detecta**: Clases y funciones sin docstrings
- **Severidad**: INFO
- **Ejemplo**:
```python
def importante():  # ⚠️ Sin docstring
    pass
```

### 9. **Dangerous Defaults** (Argumentos Peligrosos)
- **Detecta**: Valores mutables como default (list, dict)
- **Severidad**: WARNING
- **Ejemplo**:
```python
def func(items=[]):  # ⚠️ Peligroso
    items.append(1)
```

### 10. **Exception Handling** (Manejo de Excepciones)
- **Detecta**: `except:` sin especificar tipo
- **Severidad**: WARNING
- **Ejemplo**:
```python
try:
    risky_operation()
except:  # ⚠️ Debería especificar excepción
    pass
```

### 11. **TODO Comments** (Comentarios Pendientes)
- **Detecta**: TODO, FIXME, XXX, HACK
- **Severidad**: INFO
- **Ejemplo**: `# TODO: implementar esto`

### 12. **Print Statement** (Uso de Print)
- **Detecta**: Uso de `print()` en código de producción
- **Severidad**: INFO
- **Ejemplo**: `print("debug")` (usar logging)

### 13. **Complexity Check** (Verificación de Complejidad)
- **Detecta**: Expresiones booleanas complejas
- **Severidad**: INFO
- **Ejemplo**: `if a and b or c and d or e and f:`

### 14. **Exception Handling** (Operaciones Riesgosas)
- **Detecta**: Operaciones sin try/except (open, read, etc.)
- **Severidad**: INFO
- **Ejemplo**: `open()` sin try/except

### 15. **Naming Convention** (Convenciones de Nombres)
- **Detecta**: Violaciones de PEP 8
- **Severidad**: INFO
- **Ejemplos**:
  - Clases: `myClass` ❌ → `MyClass` ✅
  - Funciones: `MyFunction` ❌ → `my_function` ✅

### 16. **Code Duplication** (Código Duplicado)
- **Detecta**: Líneas de código repetidas
- **Severidad**: INFO
- **Ejemplo**: La misma línea aparece 5+ veces

### 17. **Global Variables** (Variables Globales)
- **Detecta**: Uso de `global`
- **Severidad**: INFO
- **Ejemplo**: `global contador`

### 18. **Magic Numbers** (Números Mágicos)
- **Detecta**: Números sin nombre en código
- **Severidad**: INFO
- **Ejemplo**: `if temp > 75:` (usar constante)

### 19. **Whitespace** (Espacios en Blanco)
- **Detecta**: Espacios al final de líneas
- **Severidad**: INFO
- **Ejemplo**: `x = 5    ` (espacios al final)

### 20. **Circular Imports** (Importaciones Circulares)
- **Detecta**: Importaciones circulares potenciales
- **Severidad**: WARNING
- **Ejemplo**: A importa B, B importa A

## 📊 Interpretación de Resultados

### Niveles de Severidad

| Icono | Severidad | Significado | Acción |
|-------|-----------|-------------|--------|
| 🔴 | CRITICAL | El código no compilará | Corregir inmediatamente |
| 🟠 | ERROR | Error que causará problemas | Corregir pronto |
| 🟡 | WARNING | Mala práctica, potencial problema | Revisar y considerar |
| 🔵 | INFO | Sugerencia de mejora | Opcional |

### Ejemplo de Reporte

```
================================================================================
Analyzing: ram.py
================================================================================

📊 Found 15 issue(s) in ram.py:

🔴 CRITICAL: 1 issue(s)
  Line  825 [Syntax Check] Syntax error: expected an indented block
           → def get_stats(self):

🟠 ERROR: 2 issue(s)
  Line   45 [Indentation Check] Mixed tabs and spaces in indentation
           →     def process(self):
  Line  100 [Function Completeness] Function 'helper' has no body
           → def helper(...):

🟡 WARNING: 5 issue(s)
  Line  200 [Dangerous Defaults] Function 'init' has mutable default argument
           → def init(items=[]):
  ...

🔵 INFO: 7 issue(s)
  Line   10 [Docstring Check] Function 'calculate' is missing a docstring
           → def calculate(...):
  ...
```

## 🛠️ Soluciones Comunes

### Error CRITICAL: Sintaxis

```python
# ❌ Incorrecto
def get_stats(self):

# ✅ Correcto
def get_stats(self):
    with self.lock:
        return self.stats.copy()
```

### ERROR: Indentación Mixta

```python
# ❌ Incorrecto (tabs y espacios mezclados)
def ejemplo():
	    return True  # Tab + espacios

# ✅ Correcto (solo espacios)
def ejemplo():
    return True
```

### WARNING: Default Mutable

```python
# ❌ Incorrecto
def agregar(items=[]):
    items.append(1)
    return items

# ✅ Correcto
def agregar(items=None):
    if items is None:
        items = []
    items.append(1)
    return items
```

### INFO: Nombres de Convención

```python
# ❌ Incorrecto
class myClass:
    def MyMethod(self):
        pass

# ✅ Correcto
class MyClass:
    def my_method(self):
        pass
```

## 📈 Mejores Prácticas

### 1. Ejecutar Antes de Commit
```bash
# Siempre analizar antes de hacer commit
python code_analyzer.py .
git add .
git commit -m "Fix issues"
```

### 2. Enfocarse en CRITICAL y ERROR Primero
- Los errores CRITICAL impiden la ejecución
- Los ERROR pueden causar fallos en runtime
- Los WARNING e INFO son mejoras de calidad

### 3. Análisis Incremental
```bash
# Analizar solo archivos modificados
git diff --name-only | grep .py | xargs -I {} python code_analyzer.py {}
```

### 4. Integración con CI/CD
```yaml
# Ejemplo GitHub Actions
- name: Code Analysis
  run: python code_analyzer.py . > analysis.txt
```

## 🔧 Personalización

El analizador puede modificarse editando `code_analyzer.py`:

```python
# Cambiar longitud máxima de línea
def check_line_length(self, max_length=120):  # Cambiar 120 a tu preferencia
    ...

# Cambiar severidades
self.issues.append({
    'severity': 'INFO',  # Cambiar a WARNING, ERROR, o CRITICAL
    ...
})
```

## 📝 Notas Importantes

1. **No todo debe ser perfecto**: Los issues de INFO son sugerencias, no errores
2. **Contexto importa**: Algunas advertencias pueden ser falsas alarmas
3. **PEP 8 no es ley**: Es una guía, puede haber excepciones válidas
4. **Priorizar**: CRITICAL > ERROR > WARNING > INFO

## 🤔 Preguntas Frecuentes

### ¿El analizador reemplaza a pylint/flake8?
No, es complementario. Ofrece 20 métodos específicos pero no reemplaza herramientas establecidas.

### ¿Puedo ignorar algunos issues?
Sí, especialmente los de INFO. Usa tu juicio profesional.

### ¿Cómo arreglo todos los issues automáticamente?
No hay forma automática 100% segura. Usa herramientas como `autopep8` o `black` para formateo, pero revisa manualmente.

### ¿El análisis afecta el código?
No, el analizador solo lee y reporta, nunca modifica archivos.

## 📚 Recursos Adicionales

- [PEP 8 - Style Guide](https://www.python.org/dev/peps/pep-0008/)
- [PEP 257 - Docstring Conventions](https://www.python.org/dev/peps/pep-0257/)
- [Python Best Practices](https://docs.python-guide.org/)

---

💡 **Tip**: Ejecuta el analizador regularmente para mantener la calidad del código.
