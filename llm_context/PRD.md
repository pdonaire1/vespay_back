# VesPay: Documento de Requerimientos del Producto (PRD) Actualizado

## 1. Visión General
VesPay es una super-app de pagos diseñada para unificar el ecosistema financiero fragmentado. Actúa como un hub que integra banca nacional (Pago Móvil), carteras internacionales (PayPal), criptomonedas (Binance) y pagos con tarjeta, utilizando tecnología NFC y QR para simplificar la experiencia del usuario.

## 2. Mapa de Pantallas y Requerimientos Funcionales

### A. Flujo de Autenticación y Seguridad
1.  **Iniciar Sesión ({{DATA:SCREEN:SCREEN_6}}):**
    *   **Funcionalidad:** Acceso mediante credenciales tradicionales o SSO (Google/Apple).
    *   **Requerimiento:** Validación de formato de correo y enmascaramiento de contraseña.
2.  **Verificar Correo ({{DATA:SCREEN:SCREEN_4}}):**
    *   **Funcionalidad:** Segundo factor de autenticación vía OTP de 6 dígitos.
    *   **Requerimiento:** Temporizador de reenvío y enfoque automático en los inputs.
3.  **Configurar Seguridad ({{DATA:SCREEN:SCREEN_2}}):**
    *   **Funcionalidad:** Onboarding de seguridad avanzada (Google Authenticator y Biometría).
    *   **Requerimiento:** Opción de omitir para reducir la fricción inicial.

### B. Dashboard y Gestión de Fondos
4.  **Dashboard Principal ({{DATA:SCREEN:SCREEN_27}}):**
    *   **Funcionalidad:** Resumen de saldos totales y acceso rápido a acciones principales (Enviar, Recibir, Intercambiar).
5.  **Historial de Transacciones ({{DATA:SCREEN:SCREEN_24}}):**
    *   **Funcionalidad:** Listado cronológico de movimientos con filtros por método de pago.
6.  **Detalle de Cuenta PayPal ({{DATA:SCREEN:SCREEN_12}}):**
    *   **Funcionalidad:** Gestión específica de fondos en PayPal, permitiendo añadir o retirar dinero.
7.  **Intercambio de Divisas ({{DATA:SCREEN:SCREEN_14}}):**
    *   **Funcionalidad:** Conversión en tiempo real entre billeteras vinculadas (ej. PayPal a Pago Móvil).

### C. Pagos y Recaudación (NFC/QR)
8.  **Configurar Cobro ({{DATA:SCREEN:SCREEN_17}}):**
    *   **Funcionalidad:** Selección previa entre cobro recurrente, último monto o ingreso manual.
9.  **Recibir Pago QR/NFC ({{DATA:SCREEN:SCREEN_20}}):**
    *   **Funcionalidad:** Generación de código QR dinámico y activación de antena NFC para recepción.
10. **Ingresar Monto Manual ({{DATA:SCREEN:SCREEN_16}}):**
    *   **Funcionalidad:** Teclado numérico optimizado para definir montos específicos de envío/cobro.
11. **Pago NFC Contactless ({{DATA:SCREEN:SCREEN_25}}):**
    *   **Funcionalidad:** Interfaz de "Hold Near Terminal" para pagos rápidos en puntos de venta.

### D. Módulo de Servicios
12. **Mis Servicios Pagados ({{DATA:SCREEN:SCREEN_10}}):**
    *   **Funcionalidad:** Centro de control para facturas de electricidad, agua, internet, etc.
13. **Configurar Servicio ({{DATA:SCREEN:SCREEN_8}}):**
    *   **Funcionalidad:** Vinculación de contrato con un método de pago y toggle de pago automático.

### E. Ecosistema para Terceros (Widget)
14. **Widget de Pago ({{DATA:SCREEN:SCREEN_21}}):**
    *   **Funcionalidad:** Componente integrable para apps de terceros con branding personalizable (Verde).
15. **Selección de Pago ({{DATA:SCREEN:SCREEN_18}}):**
    *   **Funcionalidad:** Selector de método dentro del flujo del widget externo.
16. **Confirmación y Onboarding ({{DATA:SCREEN:SCREEN_22}}):**
    *   **Funcionalidad:** Pantalla final de éxito que invita al usuario del widget a descargar la app completa de VesPay.

## 3. Especificaciones Técnicas
*   **Diseño:** Sistema "VesPay Fintech Core" (Azul #0046ff, Inter, Rounded-md).
*   **Arquitectura:** Patrón Abstract Factory para procesadores de pago (PayPal, Binance, Pago Móvil).
*   **Interoperabilidad:** Integración mediante WebSockets para flujos NFC en tiempo real.
