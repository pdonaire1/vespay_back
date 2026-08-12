# VesPay.md

```markdown
# Product Requirement Document (PRD) — VesPay Fintech Core

**Nombre del Producto:** VesPay  
**Design System:** VesPay Fintech Core  
**Fecha:** 7 de Agosto, 2026  
**Versión:** 2.0  
**Estado:** Especificación Técnica & UI/UX Final

---

## 1. Resumen Ejecutivo y Objetivos

VesPay es una plataforma de procesamiento e integración de pagos multicanal orientada a resolver la fragmentación transaccional en Venezuela y América Latina. Consolida en un único ecosistema:

- **Moneda Local:** Pago Móvil (Bs.) y Transferencias Bancarias Directas (con detección automática por API).
- **Plataformas Internacionales & Crypto:** Binance Pay, PayPal, Zelle y Tarjetas de Crédito/Débito Internacionales.
- **Pagos Presenciales:** Comunicación de campo cercano (NFC) sin contacto.
- **Integración a Terceros:** API REST/Webhooks tipo Stripe y el widget ultraligero web `vepay_js`.

---

## 2. Sistema de Diseño & Design Tokens (VesPay Fintech Core)

La interfaz se rige por un enfoque Modern Corporate de alta visibilidad, equilibrio táctil y estructura "Card-on-Canvas".

### 2.1 Paleta de Colores (Tokens)

```yaml
tokens:
  brand:
    primary: '#0034c5'
    on-primary: '#ffffff'
    primary-container: '#0046ff'
    on-primary-container: '#d3d9ff'
    surface-tint: '#0045fc'
  secondary:
    secondary: '#006a62'
    on-secondary: '#ffffff'
    secondary-container: '#57fae9'
    on-secondary-container: '#007168'
  tertiary:
    tertiary: '#394863'
    on-tertiary: '#ffffff'
    tertiary-container: '#51607c'
    on-tertiary-container: '#cbdbfb'
  surfaces:
    surface: '#f8f9ff'
    surface-dim: '#cbdbf5'
    surface-bright: '#f8f9ff'
    surface-container-lowest: '#ffffff'
    surface-container-low: '#eff4ff'
    surface-container: '#e5eeff'
    surface-container-high: '#dce9ff'
    surface-container-highest: '#d3e4fe'
    on-surface: '#0b1c30'
    on-surface-variant: '#434657'
    inverse-surface: '#213145'
    inverse-on-surface: '#eaf1ff'
  semantic:
    outline: '#747688'
    outline-variant: '#c4c5da'
    error: '#ba1a1a'
    on-error: '#ffffff'
    error-container: '#ffdad6'
    on-error-container: '#93000a'
```

### 2.2 Tipografía

| Token Role | Font Family | Size | Weight | Line Height | Tracking | Uso Principal |
|------------|-------------|------|--------|-------------|----------|---------------|
| display-lg | Inter | 48px | 700 | 56px | -0.02em | Landing / Pantallas de impacto |
| headline-lg | Inter | 32px | 600 | 40px | -0.01em | Encabezados de Dashboard |
| headline-lg-mobile | Inter | 24px | 600 | 32px | 0 | Encabezados en Móvil |
| headline-md | Inter | 24px | 600 | 32px | 0 | Modales y Títulos de sección |
| body-lg | Inter | 18px | 400 | 28px | 0 | Párrafos principales |
| body-md | Inter | 16px | 400 | 24px | 0 | Contenido y descripciones |
| label-md | JetBrains Mono | 14px | 500 | 20px | 0 | TX Hash, Cédula, Bancos, Monedas |
| label-sm | Inter | 12px | 600 | 16px | 0 | Badges y Chips de Estado |

### 2.3 Espaciado y Bordes

- **Grid:** Base 4px. Layout móvil de 4 columnas (márgenes 16px, gutters 16px); Desktop de 12 columnas (márgenes 32px, gutters 24px).
- **Bordes / Radius:**
  - **sm** (0.25rem / 4px): Checkboxes, badges pequeños.
  - **DEFAULT** (0.5rem / 8px): Campos de texto (input), botones secundarios, elementos de listas.
  - **md** (0.75rem / 12px): Botones primarios, modales flotantes.
  - **lg** (1rem / 16px): Tarjetas principales (Cards) y contenedor de widgets.
  - **full** (9999px): Chips de estado (Completed, Pending).

---

## 3. Arquitectura del Sistema (Patrón Abstract Factory)

Para garantizar la extensibilidad y estandarización de métodos de pago heterogéneos, el backend de VesPay adopta un patrón Abstract Factory. Este abstrae la complejidad de procesamiento bajo una única interfaz cohesiva: `Payment::create(method)`.

```
                   +--------------------------------+
                    |     AbstractPaymentFactory     |
                    +--------------------------------+
                                    |
     +------------------------------+------------------------------+
     |                              |                              |
+----+--------------------+   +-----+------------------+   +-------+------------------+
| PaypalPaymentFactory    |   | BinancePaymentFactory  |   | PagoMovilPaymentFactory  |
+-------------------------+   +------------------------+   +--------------------------+
     |                              |                              |
     v                              v                              v
+-------------------------+   +------------------------+   +--------------------------+
| PaypalProcessorService  |   | BinanceProcessorService|   | PagoMovilProcessorService|
+-------------------------+   +------------------------+   +--------------------------+
```

### 3.1 Definición de Clases e Interfaz (TypeScript Enterprise Style)

```typescript
// Enums para Métodos y Estados de Pago
export enum PaymentMethod {
  PAYPAL = 'PAYPAL',
  BINANCE = 'BINANCE',
  PAGO_MOVIL = 'PAGO_MOVIL',
  ZELLE = 'ZELLE',
  CREDIT_CARD = 'CREDIT_CARD',
  BANK_TRANSFER = 'BANK_TRANSFER'
}

export enum PaymentStatus {
  PENDING = 'PENDING',
  PROCESSING = 'PROCESSING',
  COMPLETED = 'COMPLETED',
  FAILED = 'FAILED'
}

export interface PaymentRequestDTO {
  amount: number;
  currency: string;
  senderId: string;
  recipientId: string;
  metadata?: Record<string, any>;
}

export interface PaymentResponseDTO {
  transactionId: string;
  status: PaymentStatus;
  timestamp: string;
  feeApplied: number;
  netAmount: number;
}

// Interfaz del Procesador Abstracto
export interface IPaymentProcessor {
  validateCredentials(accountDetails: any): Promise<boolean>;
  execute(request: PaymentRequestDTO): Promise<PaymentResponseDTO>;
  checkStatus(transactionId: string): Promise<PaymentStatus>;
}

// Fábrica Concreta y Fachada de Entrada
export class Payment {
  public static create(method: PaymentMethod): IPaymentProcessor {
    switch (method) {
      case PaymentMethod.PAYPAL:
        return new PaypalProcessorService();
      case PaymentMethod.BINANCE:
        return new BinanceProcessorService();
      case PaymentMethod.PAGO_MOVIL:
        return new PagoMovilProcessorService();
      case PaymentMethod.ZELLE:
        return new ZelleProcessorService();
      default:
        throw new Error(`[VesPay Error] Método de pago no soportado: ${method}`);
    }
  }
}
```

---

## 4. Requerimientos Funcionales y Flujos

### 4.1 Configuración de Cuentas y Detección Automática por API

- **Vincular Cuenta:** Los usuarios registran sus credenciales (Ej: API Keys de Binance, Client ID de PayPal, Parámetros de Pago Móvil: Cédula, Banco, Teléfono).
- **Autodetección:** El sistema cuenta con trabajadores de escucha en segundo plano (Webhooks listeners y Polling vía Workers) que detectan la acreditación inmediata de fondos sin requerir reportes manuales.

### 4.2 Algoritmo de Coincidencia Automático (Matchmaking Engine)

Cuando ocurre una interacción de cobro/pago (vía NFC, QR o Link):

1. **Paso 1:** Extraer el método preferido/por defecto definido por el Receptor.
2. **Paso 2:** Si el Emisor posee configurado y activo ese mismo método, se efectúa la transacción directamente.
3. **Paso 3:** En caso de no haber coincidencia, el motor cruza las plataformas vinculadas de ambos y selecciona la opción con mayor frecuencia de uso previa (Match).
4. **Paso 4:** Si no existe ningún cruce de plataformas, la App solicita al emisor seleccionar uno de los métodos aceptados por el receptor.

### 4.3 Integración NFC & Handshake por Socket

- **Contacto de Dispositivos:** Se inicia un token de sesión `NFC_SESSION_ID` vía campo cercano entre vendedor y pagador.
- **Streaming de Estado (WebSocket):** Inmediatamente se abre una conexión bidireccional sobre `wss://stream.vespay.io/nfc/{sessionId}`.
- **Retroalimentación Dinámica:** La pantalla de ambos dispositivos transmite el estado en tiempo real (Procesando → Éxito).

```
[ Emisor (NFC) ]  ---- Touch / Handshake ---->  [ Receptor (NFC) ]
       |                                                |
       +------------ WebSocket Connection --------------+
                               |
                               v
               wss://stream.vespay.io/nfc/{id}
                               |
                   +-----------+-----------+
                   | STATUS: PROCESSING   |
                   | STATUS: COMPLETED    |
                   +-----------------------+
```

### 4.4 Motor de Comisiones (Fee Engine)

- **Regla Global:** El administrador define un porcentaje e importe fijo para la plataforma (ej. 1.2% + $0.20 USD).
- **Regla Override por App de Tercero:** Opción para ajustar comisiones preferenciales por cada `app_id` externa registrada en el Dashboard Administrador.

---

## 5. Módulo Widget para Terceros (`vepay_js`)

### 5.1 Especificación del Flujo de Conversión Progresiva

```
1. [App Tercero] -> Invocación `vepay_js.pay({ ... })`
2. [Modal / iFrame] -> Renderiza Formulario Minimalista de Pago
3. [Procesamiento] -> Checkmark Animado "Pago Satisfactorio"
4. [Callout Conversion] -> "¿Desea guardar estos datos para futuros pagos?" 
                           [ Botón: Continuar con Google ]
5. [Continuidad] -> Muestra opción: "¿Desea descargar la App de VesPay o continuar?"
6. [Retorno] -> Cierre de Widget y Redirección a la App del tercero sin fricción.
```

### 5.2 Implementación Técnica de `vepay_js` (Frontend Snippet)

```javascript
(function (window, document) {
  'use strict';

  const VESPAY_WIDGET_URL = 'https://widget.vespay.io/checkout';

  class VesPayWidget {
    constructor() {
      this.iframe = null;
    }

    init(options) {
      this.apiKey = options.apiKey;
      this.amount = options.amount;
      this.currency = options.currency || 'USD';
      this.onSuccess = options.onSuccess || function () {};
      this.onError = options.onError || function () {};
    }

    open() {
      const src = `${VESPAY_WIDGET_URL}?key=${encodeURIComponent(this.apiKey)}&amount=${this.amount}&currency=${this.currency}`;
      
      this.iframe = document.createElement('iframe');
      this.iframe.src = src;
      this.iframe.id = 'vespay-checkout-iframe';
      this.iframe.style.cssText = `
        position: fixed;
        top: 0; left: 0; width: 100vw; height: 100vh;
        border: none; z-index: 999999;
        background: rgba(11, 28, 48, 0.6);
        backdrop-filter: blur(4px);
      `;

      document.body.appendChild(this.iframe);
      window.addEventListener('message', this._handleMessage.bind(this));
    }

    _handleMessage(event) {
      if (event.origin !== 'https://widget.vespay.io') return;

      const { type, payload } = event.data;
      if (type === 'VESPAY_SUCCESS') {
        this.onSuccess(payload);
      } else if (type === 'VESPAY_CLOSE') {
        this.close();
      } else if (type === 'VESPAY_ERROR') {
        this.onError(payload);
      }
    }

    close() {
      if (this.iframe) {
        document.body.removeChild(this.iframe);
        this.iframe = null;
      }
    }
  }

  window.VesPay = new VesPayWidget();
})(window, document);
```

---

## 6. Interfaz de Usuario (UI/UX) y Componentes

### 6.1 Estilo de Componentes Frontend (CSS/Tailwind Reference using Tokens)

```css
/* Botón Primario VesPay Core */
.vespay-btn-primary {
  background-color: #0034c5; /* primary */
  color: #ffffff;            /* on-primary */
  border-radius: 0.75rem;    /* rounded-md (12px) */
  font-family: 'Inter', sans-serif;
  font-weight: 600;
  font-size: 16px;
  padding: 12px 24px;
  border: none;
  box-shadow: 0px 10px 15px -3px rgba(0, 0, 0, 0.08);
  transition: background-color 0.2s ease, transform 0.1s ease;
}

.vespay-btn-primary:hover {
  background-color: #0046ff; /* primary-container */
}

/* Campo de Entrada de Moneda / Transacciones */
.vespay-input {
  background-color: #eff4ff; /* surface-container-low */
  border: 1px solid #c4c5da; /* outline-variant */
  border-radius: 0.5rem;     /* rounded-default (8px) */
  color: #0b1c30;            /* on-surface */
  font-family: 'Inter', sans-serif;
  padding: 12px 16px;
}

.vespay-input:focus {
  outline: 2px solid #0045fc;/* surface-tint */
  background-color: #ffffff; /* surface-container-lowest */
}

/* Identificador Monospaciado */
.vespay-mono-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 14px;
  color: #434657;            /* on-surface-variant */
}

/* Card Contenedora */
.vespay-card {
  background-color: #ffffff; /* surface-container-lowest */
  border: 1px solid #e5eeff;  /* surface-container */
  border-radius: 1rem;       /* rounded-lg (16px) */
  padding: 24px;
  box-shadow: 0px 1px 3px rgba(0, 0, 0, 0.05);
}
```

### 6.2 Micro-interacciones Requeridas

- **Loader de Carga:** Anillo giratorio con color `#0045fc` (surface-tint) sobre superficie `#eff4ff`.
- **Éxito (Checkmark):** Trazo SVG animado con color `#006a62` (secondary).
- **Estado NFC:** Pulsación de ondas radiales en color `#0046ff` sobre el ícono de contacto del teléfono.

---

## 7. Matriz de Requerimientos No Funcionales

- **Seguridad:** Cifrado de credenciales de pago bajo AES-256-GCM. Cumplimiento con estándares PCI-DSS para el manejo de tarjetas.
- **Latencia:** Notificación por WebSocket en menos de 500 ms tras la confirmación de la pasarela originaria.
- **Compatibilidad:** El widget `vepay_js` debe pesar menos de 18 KB gzipped y operar eficientemente en navegadores móviles (iOS Safari / Android Chrome).

---

