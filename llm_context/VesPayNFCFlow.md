Especificación Técnica: Flujo de Pago Contactless (NFC) — VesPay
1. Diagrama de Secuencia y Arquitectura

sequenceDiagram
    autonumber
    actor Pagador as Pagador (Cliente)
    participant AppPagador as App / Wallet Cliente
    participant Backend as Backend VesPay (Core API)
    participant AppReceptor as App / POS Receptor
    actor Receptor as Receptor (Comercio)
    participant Pasarela as Plataforma Tercero (Binance / PayPal / Pago Móvil)

    %% Paso 1
    rect rgb(239, 244, 255)
    Note over Pagador, Backend: Paso 1: Solicitud e Iniciación de Token Pagador
    Pagador->>AppPagador: Inicia solicitud de pago
    AppPagador->>Backend: POST /api/v1/nfc/payer-token (auth, wallet_id)
    Backend-->>AppPagador: Retorna `PAYER_TOKEN` (Token Efímero Cifrado)
    end

    %% Paso 2
    rect rgb(248, 249, 255)
    Note over Receptor, Backend: Paso 2: Generación de Token de Cobro
    Receptor->>AppReceptor: Ingresa monto de cobro
    AppReceptor->>Backend: POST /api/v1/nfc/payee-token (amount, currency, merchant_id)
    Backend-->>AppReceptor: Retorna `PAYEE_TOKEN` (Token de Orden de Cobro)
    end

    %% Paso 3
    rect rgb(230, 250, 248)
    Note over AppPagador, AppReceptor: Paso 3: Contacto NFC y Handshake de Tokens
    Pagador->>AppReceptor: Acerca el teléfono (NFC Touch)
    AppPagador->>AppReceptor: Transmisión NFC: Envíia `PAYER_TOKEN`
    AppReceptor->>Backend: POST /api/v1/nfc/process-payment { PAYER_TOKEN, PAYEE_TOKEN }
    end

    %% Paso 4
    rect rgb(211, 228, 254)
    Note over Backend, Pasarela: Paso 4: Validaciones y Procesamiento en Terceros
    Backend->>Backend: Valida firmas de tokens, expiración y matchmaking de métodos
    Backend->>Pasarela: Ejecuta débito/transferencia en pasarela seleccionada
    Pasarela-->>Backend: Respuesta: Transacción Exitosa / Hash
    Backend-->>AppPagador: Stream WebSocket: STATUS_COMPLETED (Pago Exitoso)
    Backend-->>AppReceptor: Stream WebSocket: STATUS_COMPLETED (Cobro Exitoso)
    
    


Flujo de pago **NFC Contactless** de VesPay, estructurada paso a paso para documentación técnica, manuales de usuario o guías de integración de desarrolladores:

---

# Guía Paso a Paso: Flujo de Pago NFC Contactless (Dual-Token)

Este flujo describe la interacción paso a paso entre el **Pagador**, el **Receptor**, el **Backend de VesPay** y las **Plataformas de Terceros** (Binance Pay, PayPal, Pago Móvil, etc.) mediante el protocolo de seguridad de **Doble Token**.

---

## 📋 Resumen del Proceso

| Paso | Actor Principal | Acción | Resultado |
| --- | --- | --- | --- |
| **Paso 1** | Pagador (Cliente) | Solicita token de pago seguro | Se genera `PAYER_TOKEN` en el Backend |
| **Paso 2** | Receptor (Comercio) | Genera orden de cobro con monto | Se genera `PAYEE_TOKEN` en el Backend |
| **Paso 3** | Pagador + Receptor | Contacto físico NFC (Touch) | El Receptor recibe el `PAYER_TOKEN` y envía la solicitud unificada |
| **Paso 4** | Backend VesPay | Procesa el pago en el tercero | Confirmación en tiempo real por WebSockets |

---

## 🛠️ Paso a Paso Detallado

### 🔹 Paso 1: Creación del Token del Pagador

1. El cliente abre la App de **VesPay** y presiona **"Pagar con NFC"**.
2. La aplicación del cliente realiza una petición autenticada al API Core:
```http
POST /api/v1/nfc/payer-token
Authorization: Bearer <token_sesion_pagador>

```


3. El backend de VesPay valida el estado de la cuenta del usuario y genera un **`PAYER_TOKEN`** efímero y firmado cifradamente (HMAC-SHA256) con validez de 120 segundos.
4. El teléfono del pagador almacena temporalmente este token y habilita la antena NFC en modo de transmisión.

---

### 🔹 Paso 2: Generación del Token de Cobro del Receptor

1. El vendedor o comercio ingresa el monto a cobrar en su App de VesPay (ej. `$5.00 USD` o `Bs. 180.00`).
2. La app del receptor solicita la creación de una orden de cobro:
```http
POST /api/v1/nfc/payee-token
Authorization: Bearer <token_sesion_receptor>
Content-Type: application/json

{
  "amount": 5.00,
  "currency": "USD"
}

```


3. El backend responde con un **`PAYEE_TOKEN`** que identifica de forma única la intención de cobro.
4. El dispositivo del receptor habilita la antena NFC para escuchar la transmisión del pagador.

---

### 🔹 Paso 3: Contacto NFC y Handshake de Tokens

1. El pagador aproxima su smartphone al teléfono o terminal del receptor (distancia $< 4\text{ cm}$).
2. A través del canal de campo cercano (NFC), la app del pagador envía el **`PAYER_TOKEN`** al dispositivo del receptor.
3. El dispositivo del receptor recibe el token del pagador, los junta y genera una **Solicitud Unificada de Pago**:
```http
POST /api/v1/nfc/process-payment
Content-Type: application/json

{
  "payer_token": "vsp_ptk_8f912a7e4b01d90c",
  "payee_token": "vsp_ytk_991823710293148a"
}

```



---

### 🔹 Paso 4: Procesamiento y Confirmación en Tiempo Real

1. **Validación Backend:** El servidor de VesPay recibe ambos tokens, comprueba que estén vigentes, no hayan sido usados previamente y verifica los métodos de pago coincidentes entre ambos usuarios mediante el motor de *Matchmaking*.
2. **Ejecución en Tercero:** La fachada `Payment::create()` ejecuta el débito/transferencia en la plataforma elegida (ej. Binance Pay o Pago Móvil).
3. **Notificación Instantánea (Sockets):** Mediante la conexión abierta `wss://stream.vespay.io/nfc/{sessionId}`, el backend transmite el evento final en tiempo real:
```json
{
  "event": "PAYMENT_SUCCESS",
  "status": "COMPLETED",
  "transaction_id": "tx_nfc_772184019283",
  "amount": 5.00,
  "currency": "USD"
}

```


4. Ambos dispositivos vibran y muestran la pantalla de **"Pago Satisfactorio"** con el checkmark animado en menos de 800 ms.