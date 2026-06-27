# 🎨 Frontend - Telegram Bot Integratsiyasi

## 📋 Frontend-da Nima Qo'shish Kerak

### 1️⃣ User Profile Page-ga Telegram Linking Button

**Location:** `Settings / Profile / Telegram Section`

```jsx
// Frontend Component (pseudocode)
function TelegramLinking({ userId, currentTelegramId }) {
  const [linking, setLinking] = useState(false);
  
  const handleLink = async () => {
    const response = await fetch(`/api/users/${userId}/telegram/link`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const data = await response.json();
    // Show: data.telegram_link button
    // Message: data.message
  };
  
  const handleUnlink = async () => {
    await fetch(`/api/users/${userId}/telegram/unlink`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    });
    // Refresh user data
  };
  
  return (
    <div className="telegram-section">
      {currentTelegramId ? (
        <>
          <p>✅ Telegram bog'langan</p>
          <button onClick={handleUnlink}>
            Bog'lanishni o'chirish
          </button>
        </>
      ) : (
        <>
          <p>❌ Telegram bog'lanmagan</p>
          <button onClick={handleLink}>
            🔗 Telegramga bog'lan
          </button>
        </>
      )}
    </div>
  );
}
```

### 2️⃣ Link Dialog Component

```jsx
// When link token is created
function TelegramLinkDialog({ linkData, onClose }) {
  return (
    <Dialog>
      <h2>🔗 Telegramga Bog'lan</h2>
      
      <p>Telegram-da quyidagi linkni bosing:</p>
      <a 
        href={linkData.telegram_link}
        className="btn btn-primary"
        target="_blank"
      >
        📱 Telegram-da Ochish
      </a>
      
      <p>Yoki token-ni qo'pish qiling:</p>
      <input 
        type="text" 
        value={linkData.token} 
        readOnly 
      />
      
      <p>Keyin Telegram-da yuboring:</p>
      <code>/link {linkData.token}</code>
      
      <button onClick={onClose}>Yopish</button>
    </Dialog>
  );
}
```

### 3️⃣ User Profile Display

```jsx
// User profile ma'lumotlarida Telegram status
function UserProfileCard({ user }) {
  return (
    <Card>
      <h3>{user.full_name}</h3>
      <p>Email: {user.email}</p>
      <p>Rol: {user.role}</p>
      
      {/* NEW */}
      <p>
        Telegram: 
        {user.telegram_chat_id ? (
          <span className="success">✅ Bog'langan ({user.telegram_chat_id})</span>
        ) : (
          <span className="warning">❌ Bog'lanmagan</span>
        )}
      </p>
    </Card>
  );
}
```

---

## 🎯 UI Layout Suggestion

### Profile Settings Page

```
┌─────────────────────────────────┐
│ User Profile Settings           │
├─────────────────────────────────┤
│                                 │
│ Profil Ma'lumotlari              │
│ ├─ Ism: Jahongir                │
│ ├─ Email: jahongir@example.com  │
│ └─ Rol: Designer                │
│                                 │
│ Telegram Bog'lanishi            │
│ ├─ Status: ✅ Bog'langan        │
│ ├─ Telegram ID: 521013738       │
│ └─ [Bog'lanishni O'chirish]      │
│                                 │
│ Mini App                         │
│ └─ [Mini App-ni Ochish]          │
│                                 │
└─────────────────────────────────┘
```

### Telegram Linking Dialog

```
┌──────────────────────────────────┐
│ 🔗 Telegramga Bog'lan           │
├──────────────────────────────────┤
│                                  │
│ Telegram-da quyidagi linkni bosing:
│                                  │
│ ┌────────────────────────────┐  │
│ │ 📱 Telegram-da Ochish     │  │
│ └────────────────────────────┘  │
│                                  │
│ Yoki token-ni copy qiling:      │
│ ┌──────────────────────────────┐ │
│ │ abc123xyz...                │ │
│ │ [Copy]                       │ │
│ └──────────────────────────────┘ │
│                                  │
│ Keyin Telegram-da yuboring:     │
│ /link abc123xyz...              │
│                                  │
│ [Yopish]                        │
└──────────────────────────────────┘
```

---

## 🔗 Integration Points

### 1. Login Response
```json
{
  "access_token": "...",
  "user": {
    "id": "abc123",
    "email": "user@example.com",
    "telegram_chat_id": "521013738",
    "role": "designer"
  }
}
```

### 2. Update User Endpoint
```
PUT /api/users/{id}
{
  "telegram_chat_id": "521013738"  // Read-only, set via linking
}
```

### 3. Telegram Link Endpoint
```
POST /api/users/{id}/telegram/link
Response:
{
  "telegram_link": "https://t.me/AiSupport1_bot?start=link_abc123...",
  "message": "Linkni bosing yoki tokenni yuboring",
  "token": "abc123..."
}
```

---

## 💻 Code Examples

### React Hook for Telegram Linking

```javascript
// useTelegramLink.js
import { useState } from 'react';

export function useTelegramLink(userId, accessToken) {
  const [loading, setLoading] = useState(false);
  const [linkData, setLinkData] = useState(null);
  const [error, setError] = useState(null);

  const createLink = async () => {
    setLoading(true);
    try {
      const response = await fetch(
        `/api/users/${userId}/telegram/link`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json',
          },
        }
      );
      const data = await response.json();
      setLinkData(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const removeLink = async () => {
    setLoading(true);
    try {
      await fetch(`/api/users/${userId}/telegram/unlink`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
        },
      });
      setLinkData(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return { loading, linkData, error, createLink, removeLink };
}
```

### Usage in Component

```jsx
function ProfilePage() {
  const { user, token } = useAuth();
  const { linkData, createLink, removeLink, loading } = 
    useTelegramLink(user.id, token);

  return (
    <div>
      <h2>Profil</h2>
      
      <div className="telegram-section">
        <h3>Telegram Bog'lanishi</h3>
        
        {user.telegram_chat_id ? (
          <div>
            <p className="success">✅ Bog'langan</p>
            <button onClick={removeLink} disabled={loading}>
              Bog'lanishni O'chirish
            </button>
          </div>
        ) : (
          <div>
            <p className="warning">❌ Bog'lanmagan</p>
            <button onClick={createLink} disabled={loading}>
              Telegramga Bog'lan
            </button>
          </div>
        )}
      </div>

      {linkData && (
        <TelegramLinkDialog 
          linkData={linkData} 
          onClose={() => setLinkData(null)}
        />
      )}
    </div>
  );
}
```

---

## 🎨 CSS Styling

```css
.telegram-section {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px;
  border-radius: 8px;
  margin: 20px 0;
}

.telegram-section h3 {
  margin-top: 0;
  display: flex;
  align-items: center;
  gap: 10px;
}

.telegram-section .status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  margin: 10px 0;
}

.telegram-section .status.success::before {
  content: "✅";
}

.telegram-section .status.warning::before {
  content: "❌";
}

.telegram-section button {
  background: white;
  color: #667eea;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.telegram-section button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.telegram-link-dialog {
  background: white;
  padding: 30px;
  border-radius: 12px;
  max-width: 400px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.telegram-link-dialog a.btn {
  display: block;
  text-align: center;
  padding: 12px;
  background: #667eea;
  color: white;
  text-decoration: none;
  border-radius: 6px;
  margin: 15px 0;
  font-weight: 600;
}

.telegram-link-dialog code {
  background: #f0f0f0;
  padding: 8px 12px;
  border-radius: 4px;
  display: block;
  margin: 10px 0;
  word-break: break-all;
}
```

---

## 🧪 Testing

### Manual Testing Checklist

- [ ] Profile page-da Telegram section ko'rinadi
- [ ] "Telegramga Bog'lan" tugmasi noquvvatli  
- [ ] Dialog chiqadi, token ko'rsatiladi
- [ ] Link Telegram-da ochiladi
- [ ] `/link token` buyrug'i Telegram-da ishlaydi
- [ ] Bog'langandan so'ng status yangilandi
- [ ] "Bog'lanishni O'chirish" tugmasi noquvvatli
- [ ] Qayta bog'lash mumkin

---

## 📱 Mobile Responsiveness

```css
@media (max-width: 768px) {
  .telegram-section {
    padding: 15px;
  }

  .telegram-link-dialog {
    max-width: 100%;
    margin: 0 auto;
  }

  .telegram-section button {
    width: 100%;
  }
}
```

---

## 🔌 API Integration Flow

```
Frontend                    Backend
   │                           │
   ├─ POST /users/{id}/link ──>│
   │                           │
   │<─ { token, link_url } ────┤
   │                           │
   ├─ Show Dialog with link ───┤
   │                           │
   │ User clicks Telegram link │
   │         │                 │
   │         └──> Telegram Bot │
   │                           │
   │ User sends /link token    │
   │ to Bot                    │
   │         │                 │
   │         └──> Bot calls POST /link
   │                    with token
   │         │          │
   │         │<─ ✅ Success
   │         │
   │ Frontend polls user data  │
   │      or receives update    │
   │         │                 │
   │         └──> Shows updated status
```

---

## 📊 State Management

```javascript
// Using Context
const TelegramContext = createContext();

function TelegramProvider({ children }) {
  const [linked, setLinked] = useState(false);
  const [telegramId, setTelegramId] = useState(null);
  const [linking, setLinking] = useState(false);

  return (
    <TelegramContext.Provider value={{
      linked,
      telegramId,
      linking,
      setLinked,
      setTelegramId,
      setLinking,
    }}>
      {children}
    </TelegramContext.Provider>
  );
}

// Usage
const { linked, linking } = useContext(TelegramContext);
```

---

**Integration Guide Version**: 1.0.0  
**Frontend Ready**: ✅ Prepared  
**Backend Ready**: ✅ Running  

Qo'shimcha: UI components-ni `src/components/Telegram/` papkasiga joylashtiring.
