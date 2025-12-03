# Factos2 - Optimus Prime System Optimizer

Sistema avanzado de optimización de Windows con interfaz gráfica para control de módulos.

## 🚀 Características

- **12 Módulos de Optimización** independientes y configurables
- **Interfaz Gráfica** intuitiva para activar/desactivar módulos
- **Análisis de Código** con 20 métodos de verificación
- **Optimización en Tiempo Real** de recursos del sistema

## 📦 Módulos Disponibles

1. **Almacenamiento** - Optimización de disco, cache y operaciones I/O
2. **GPU** - Gestión de tarjeta gráfica y renderizado
3. **RAM** - Administración inteligente de memoria
4. **Kernel** - Optimizaciones a nivel del núcleo del sistema
5. **CPU** - Control de procesador, núcleos y frecuencias
6. **Prioridades** - Gestión dinámica de prioridades de procesos
7. **Energía** - Administración de consumo energético
8. **Temperatura** - Monitoreo y gestión térmica
9. **Servicios** - Control de servicios de Windows
10. **Redes** - Optimización de red y TCP/IP
11. **Perfiles** - Perfiles automáticos según escenario de uso
12. **Ajustes Varios** - Optimizaciones generales del sistema

## 🔧 Instalación

### Requisitos
- Windows 10/11
- Python 3.8 o superior
- Privilegios de administrador

### Pasos de Instalación

```bash
# 1. Clonar el repositorio
git clone https://github.com/moltenisoy/factos2.git
cd factos2

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Ejecutar el launcher (como administrador)
python launcher.py
```

## 🖥️ Uso

### Launcher Gráfico

1. Ejecutar `launcher.py` como administrador
2. La interfaz muestra todos los módulos disponibles
3. Usar checkboxes para activar/desactivar módulos individualmente
4. Usar botones "Activar Todos" o "Desactivar Todos" para control masivo
5. Los indicadores de estado muestran el estado de cada módulo (verde=activo, rojo=inactivo)

### Análisis de Código

El sistema incluye un analizador completo con 20 métodos de verificación:

```bash
# Analizar todos los archivos Python en el directorio actual
python code_analyzer.py .

# Analizar un archivo específico
python code_analyzer.py archivo.py

# Analizar un directorio específico
python code_analyzer.py /ruta/al/directorio
```

#### Métodos de Análisis

1. **Syntax Check** - Errores de sintaxis de Python
2. **Indentation Check** - Verificación de indentación y espacios/tabs
3. **Function Completeness** - Funciones incompletas o vacías
4. **Unreachable Code** - Código inalcanzable después de return/raise
5. **Undefined Variables** - Variables potencialmente no definidas
6. **Unused Imports** - Importaciones no utilizadas
7. **Line Length** - Líneas que exceden 120 caracteres
8. **Docstring Check** - Documentación faltante en clases/funciones
9. **Dangerous Defaults** - Argumentos mutables por defecto
10. **Exception Handling** - Cláusulas except sin tipo específico
11. **TODO Comments** - Comentarios TODO, FIXME, XXX, HACK
12. **Print Statement** - Uso de print() en lugar de logging
13. **Complexity Check** - Expresiones booleanas complejas
14. **Exception Handling** - Operaciones riesgosas sin try/except
15. **Naming Convention** - Verificación de convenciones PEP 8
16. **Code Duplication** - Detección de código duplicado
17. **Global Variables** - Uso de variables globales
18. **Magic Numbers** - Números mágicos sin nombre
19. **Whitespace** - Espacios en blanco al final de línea
20. **Circular Imports** - Importaciones circulares potenciales

## 📊 Niveles de Severidad

- 🔴 **CRITICAL** - Errores que impiden la ejecución
- 🟠 **ERROR** - Errores que pueden causar problemas
- 🟡 **WARNING** - Advertencias sobre malas prácticas
- 🔵 **INFO** - Información para mejorar el código

## 🛠️ Desarrollo

### Estructura del Proyecto

```
factos2/
├── launcher.py           # Interfaz gráfica principal
├── core.py              # Gestor principal del sistema
├── code_analyzer.py     # Analizador de código con 20 métodos
├── almacenamiento.py    # Módulo de optimización de almacenamiento
├── gpu.py               # Módulo de optimización de GPU
├── ram.py               # Módulo de optimización de RAM
├── kernel.py            # Módulo de optimización del kernel
├── cpu.py               # Módulo de optimización de CPU
├── prioridades.py       # Módulo de gestión de prioridades
├── energia.py           # Módulo de administración de energía
├── temperatura.py       # Módulo de monitoreo térmico
├── servicios.py         # Módulo de gestión de servicios
├── redes.py             # Módulo de optimización de red
├── perfiles.py          # Módulo de perfiles automáticos
├── ajustes_varios.py    # Módulo de ajustes varios
└── requirements.txt     # Dependencias del proyecto
```

### Agregar Nuevos Módulos

1. Crear archivo del módulo (ej: `nuevo_modulo.py`)
2. Implementar las clases de optimización necesarias
3. Agregar importación en `core.py`
4. Agregar entrada en `modules_enabled` en `UnifiedProcessManager.__init__`
5. Agregar entrada en `module_info` en `launcher.py`

## 🔍 Solución de Problemas

### Error: "IndentationError"
- **Causa**: Indentación incorrecta en archivos Python
- **Solución**: Ejecutar `python code_analyzer.py .` para identificar problemas

### Error: "Access Denied"
- **Causa**: Privilegios insuficientes
- **Solución**: Ejecutar como administrador

### Módulo no responde
- **Causa**: Módulo deshabilitado o error en inicialización
- **Solución**: Verificar logs en `optimus_prime.log`

## 📝 Notas Importantes

- **Siempre ejecutar como administrador** para que las optimizaciones funcionen correctamente
- Los cambios en módulos se aplican en tiempo real
- Los logs se guardan en `optimus_prime.log`
- Se recomienda mantener "Ajustes Varios" activado para funcionalidad básica

## 🤝 Contribución

Las contribuciones son bienvenidas. Por favor:
1. Fork el proyecto
2. Crear una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir un Pull Request

## 📄 Licencia

Este proyecto es de código abierto y está disponible bajo la licencia que se especifique.

## ✨ Autor

- moltenisoy

## 🔄 Historial de Cambios

### v1.0.0 - Actual
- ✅ Corrección de errores de indentación en múltiples archivos
- ✅ Implementación de interfaz gráfica mejorada
- ✅ Analizador de código con 20 métodos de verificación
- ✅ Control individual de módulos en tiempo real
- ✅ Indicadores de estado visuales
- ✅ Documentación completa

---

⚠️ **ADVERTENCIA**: Este software realiza optimizaciones profundas del sistema. Úselo bajo su propio riesgo.
