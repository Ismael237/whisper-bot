# Devbook: WhisperBot - Bot Telegram d'Messages Anonymes MVP

## 1. Introduction

Ce document décrit l'architecture et les spécifications pour développer WhisperBot, un bot Telegram permettant aux utilisateurs de recevoir des messages anonymes via des liens uniques partagés. Le bot fonctionne comme un clone de NGL, offrant une plateforme sécurisée pour l'échange de messages anonymes entre utilisateurs.

## 2. Objectifs du MVP

### 2.1 Fonctionnalités Principales
- **Création de profil** : Enregistrement avec nom d'utilisateur et génération de lien unique
- **Messages anonymes** : Réception et envoi de messages sans révéler l'identité
- **Interface intuitive** : Boutons "Play" et "Inbox" pour navigation simplifiée
- **Partage de messages** : Fonctionnalité de partage des messages reçus
- **Pagination** : Affichage des messages un par un avec navigation
- **Statistiques** : Suivi des métriques d'utilisation
- **Gestion de compte** : Possibilité de suppression et recréation

### 2.2 Langue et Interface
- **Anglais uniquement** : Toutes les interactions en anglais
- **Interface Telegram native** : Utilisation des keyboards inline

## 3. Architecture Simplifiée

### 3.1 Structure Monolithique
L'application est un service Python unique intégrant :
- **Bot Telegram** : Interface utilisateur principale avec gestion des commandes
- **Gestionnaire de liens** : Génération et validation des liens uniques
- **Système de messages** : Traitement et stockage des messages anonymes
- **Gestionnaire de sessions** : Suivi des états utilisateurs
- **Système de statistiques** : Collecte et calcul des métriques

### 3.2 Base de Données
PostgreSQL comme unique source de données pour :
- Profils utilisateurs et authentification
- Messages anonymes et historique
- Liens uniques et mappings
- Sessions et états temporaires
- Statistiques d'utilisation

## 4. Modèle de Données

### 4.1 Utilisateurs
```
Users
- id (Primary Key)
- telegram_id (Unique)
- username (String, nom choisi par l'utilisateur)
- telegram_username (String, @username Telegram, nullable)
- unique_code (String, code aléatoire pour le lien)
- total_messages_received (Integer, compteur)
- total_messages_sent (Integer, compteur)
- is_active (Boolean, statut du compte)
- created_at (Timestamp)
- updated_at (Timestamp)
- last_activity (Timestamp)
```

### 4.2 Messages Anonymes
```
Anonymous_Messages
- id (Primary Key)
- recipient_id (Foreign Key -> Users.id)
- sender_telegram_id (BigInteger, ID Telegram de l'expéditeur)
- message_content (Text, contenu du message, max 1000 caractères)
- is_read (Boolean, statut de lecture)
- shared_count (Integer, nombre de partages)
- created_at (Timestamp)
- read_at (Timestamp, nullable)
```

### 4.3 Sessions Utilisateurs
```
User_Sessions
- id (Primary Key)
- telegram_id (BigInteger)
- session_type (Enum: 'setup', 'sending_message', 'browsing_inbox')
- target_user_id (Foreign Key -> Users.id, nullable)
- current_step (String, étape actuelle du processus)
- session_data (JSON, données temporaires)
- expires_at (Timestamp)
- created_at (Timestamp)
- updated_at (Timestamp)
```

### 4.4 Statistiques Globales
```
Global_Stats
- id (Primary Key)
- stat_date (Date, unique)
- total_users (Integer)
- active_users (Integer, activité dans les 7 derniers jours)
- messages_sent_today (Integer)
- new_registrations (Integer)
- created_at (Timestamp)
```

### 4.5 Logs d'Activité
```
Activity_Logs
- id (Primary Key)
- telegram_id (BigInteger)
- action_type (Enum: 'register', 'send_message', 'read_message', 'share_message', 'delete_account')
- details (JSON, détails de l'action)
- ip_info (String, informations de géolocalisation si disponible)
- created_at (Timestamp)
```

## 5. Fonctionnalités du Bot Telegram

### 5.1 Commandes Principales
- `/start [unique_code]` : Démarrage du bot ou accès direct à l'envoi de message
- `/play` : Activation du mode jeu et génération du lien
- `/inbox` : Consultation des messages reçus
- `/stats` : Statistiques personnelles
- `/delete` : Suppression du compte
- `/help` : Aide et instructions

### 5.2 Flux d'Enregistrement Initial
1. **Première visite** : `/start` sans paramètre
2. **Message de bienvenue** : Explication du concept et boutons principaux
3. **Affichage interface** : Boutons "🎮 Play" et "📬 Inbox"
4. **État non-joueur** : L'utilisateur peut envoyer des messages mais pas en recevoir

### 5.3 Flux d'Activation "Play"
1. **Bouton Play** : L'utilisateur clique sur "🎮 Play"
2. **Vérification profil** : Check si profil déjà créé
3. **Demande nom** : "Enter your display name for the game:"
4. **Proposition username** : Si @username Telegram existe, proposition de l'utiliser
5. **Validation nom** : Vérification unicité et format (3-20 caractères, alphanumerique)
6. **Génération lien** : Création du code unique et lien `t.me/WhisperBot?start=username_abc123`
7. **Affichage lien** : Présentation du lien avec instructions de partage
8. **Activation compte** : L'utilisateur peut maintenant recevoir des messages

### 5.4 Flux d'Envoi de Message Anonyme
1. **Accès via lien** : `/start username_abc123`
2. **Validation lien** : Vérification existence et validité du profil cible
3. **Interface envoi** : "Send an anonymous message to [username]:"
4. **Saisie message** : Capture du message (max 1000 caractères)
5. **Confirmation** : "Your message has been sent anonymously!"
6. **Sauvegarde** : Stockage du message avec metadata
7. **Notification** : Alerte au destinataire si souhaité

### 5.5 Flux de Consultation "Inbox"
1. **Bouton Inbox** : Clic sur "📬 Inbox"
2. **Vérification statut** : Check si l'utilisateur a un profil actif
3. **Redirection si nécessaire** : Vers Play si pas de profil
4. **Comptage messages** : Calcul du total de messages non lus/totaux
5. **Affichage message** : Un message à la fois avec pagination
6. **Boutons navigation** : "⬅️ Previous", "➡️ Next", "📤 Share", "🏠 Home"
7. **Marquage lecture** : Automatique lors de l'affichage

### 5.6 Flux de Partage de Message
1. **Bouton Share** : Depuis l'inbox sur un message spécifique
2. **Génération contenu** : Formatage du message pour partage externe
3. **Interface Telegram** : Utilisation du système de partage natif
4. **Compteur** : Incrémentation du compteur de partages
5. **Analytics** : Tracking de l'action de partage

### 5.7 Flux de Suppression de Compte
1. **Commande /delete** : Demande de suppression
2. **Confirmation** : "Are you sure? This will delete all your messages and deactivate your link."
3. **Double confirmation** : Bouton "Yes, delete my account"
4. **Suppression données** : Désactivation du profil et anonymisation des messages
5. **Reset interface** : Retour à l'état initial comme nouveau utilisateur

## 6. Logique Métier Détaillée

### 6.1 Génération de Liens Uniques
- **Format** : `username_randomcode` où randomcode = 8 caractères alphanumériques
- **Unicité** : Vérification en base avant génération
- **Validation** : Username 3-20 caractères, lettres/chiffres/underscore seulement
- **Persistence** : Les liens ne expirent jamais tant que le compte est actif

### 6.2 Gestion des Messages
- **Limite longueur** : Maximum 1000 caractères par message
- **Filtrage basique** : Suppression des espaces inutiles, validation UTF-8
- **Stockage** : Conservation de tous les messages pour historique
- **Notification** : Possibilité d'alerte en temps réel (optionnel)

### 6.3 Système de Pagination
- **Affichage** : Un message à la fois dans l'inbox
- **Navigation** : Boutons Previous/Next avec gestion des limites
- **État** : Sauvegarde de la position actuelle en session
- **Performance** : Chargement lazy des messages

### 6.4 Statistiques et Analytics
- **Métriques utilisateur** : Messages reçus/envoyés, date d'inscription, dernière activité
- **Métriques globales** : Utilisateurs totaux/actifs, messages du jour, nouvelles inscriptions
- **Tracking actions** : Log de toutes les actions importantes
- **Rapports** : Génération automatique de statistiques quotidiennes

### 6.5 Gestion des Sessions
- **États temporaires** : Suivi des processus multi-étapes
- **Expiration** : Nettoyage automatique après 1 heure d'inactivité
- **Persistance** : Sauvegarde des données temporaires importantes
- **Recovery** : Reprise des processus interrompus

## 7. Spécifications Techniques

### 7.1 Technologies Requises
- **Langage** : Python 3.9+
- **Framework bot** : python-telegram-bot v20+
- **Base de données** : PostgreSQL avec SQLAlchemy ORM
- **Cache** : Redis pour sessions et données temporaires
- **Tâches** : APScheduler pour les cron jobs de nettoyage
- **Monitoring** : Logging structuré avec Python logging

### 7.2 Configuration Environnement (.env)
```
# Bot Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_ADMIN_ID=admin_telegram_id
BOT_USERNAME=WhisperBot

# Base de données
DATABASE_URL=postgresql://user:pass@localhost/whisperbot_db

# Redis Cache
REDIS_URL=redis://localhost:6379/0

# Limites et paramètres
MAX_MESSAGE_LENGTH=1000
MIN_USERNAME_LENGTH=3
MAX_USERNAME_LENGTH=20
SESSION_TIMEOUT_HOURS=1

# Statistiques
ENABLE_ANALYTICS=true
CLEANUP_OLD_SESSIONS_HOURS=24

# Sécurité
RATE_LIMIT_MESSAGES_PER_HOUR=10
ENABLE_FLOOD_PROTECTION=true
```

### 7.3 Structure du Projet
```
whisperbot/
├── main.py                    # Point d'entrée principal
├── config.py                  # Configuration et variables d'environnement
├── database/
│   ├── models.py             # Modèles SQLAlchemy
│   ├── database.py           # Configuration base de données
│   └── migrations/           # Scripts de migration
├── bot/
│   ├── handlers/
│   │   ├── start_handler.py  # Gestion /start et liens
│   │   ├── play_handler.py   # Logique du mode Play
│   │   ├── inbox_handler.py  # Gestion de l'inbox
│   │   ├── message_handler.py # Envoi messages anonymes
│   │   └── admin_handler.py  # Commandes administrateur
│   ├── keyboards.py          # Claviers inline et réponses
│   ├── messages.py           # Templates de messages
│   └── middleware.py         # Middleware pour logging/stats
├── services/
│   ├── user_service.py       # Gestion des utilisateurs
│   ├── message_service.py    # Gestion des messages anonymes
│   ├── link_service.py       # Génération et validation des liens
│   ├── session_service.py    # Gestion des sessions utilisateur
│   ├── stats_service.py      # Statistiques et analytics
│   └── sharing_service.py    # Fonctionnalités de partage
├── utils/
│   ├── validators.py         # Validation des données
│   ├── formatters.py         # Formatage des messages
│   ├── generators.py         # Génération codes uniques
│   └── helpers.py            # Fonctions utilitaires
├── jobs/
│   ├── cleanup_job.py        # Nettoyage sessions expirées
│   └── stats_job.py          # Calcul statistiques quotidiennes
└── requirements.txt          # Dépendances Python
```

## 8. Interface Utilisateur

### 8.1 Messages de Bienvenue
```
🎭 Welcome to WhisperBot!

Receive anonymous messages from your friends and followers!

🎮 Play - Create your unique link to receive messages
📬 Inbox - Read your anonymous messages

How it works:
1. Click Play to create your unique link
2. Share your link anywhere
3. Receive anonymous messages in your Inbox!
```

### 8.2 Interface Play
```
🎮 PLAY MODE

Choose your display name:
This name will be shown when people send you messages.

Current name: [Not set]
Your link: [Not generated yet]

Enter your new display name:
```

### 8.3 Interface Inbox
```
📬 INBOX (Message 1 of 15)

💬 Anonymous message:
"Your presentation today was amazing! Keep up the great work!"

Received: 2 hours ago
Shared: 0 times

⬅️ Previous | ➡️ Next | 📤 Share | 🏠 Home
```

### 8.4 Interface Envoi de Message
```
💬 Send anonymous message to @username

Type your message below:
(Max 1000 characters)

Your message will be completely anonymous.
```

## 9. Sécurité et Limitations

### 9.1 Protection Anti-Spam
- **Rate limiting** : Maximum 10 messages par heure par utilisateur
- **Limitation longueur** : 1000 caractères maximum par message
- **Flood protection** : Détection des envois répétitifs
- **Validation input** : Sanitisation de tous les inputs utilisateur

### 9.2 Gestion de la Vie Privée
- **Anonymat** : Aucun lien entre expéditeur et message stocké côté destinataire
- **Logs minimaux** : Conservation uniquement des données nécessaires
- **Suppression** : Possibilité de supprimer complètement son compte
- **GDPR compliance** : Respect des réglementations sur les données

### 9.3 Validation des Données
- **Noms d'utilisateur** : Alphanumériques uniquement, 3-20 caractères
- **Messages** : Validation UTF-8, suppression caractères dangereux
- **Liens** : Vérification format et existence avant traitement
- **Sessions** : Expiration automatique et nettoyage

## 10. Gestion des Erreurs

### 10.1 Erreurs Utilisateur
- **Nom déjà pris** : "This username is already taken. Please choose another."
- **Message trop long** : "Message too long. Maximum 1000 characters."
- **Lien invalide** : "This link is invalid or expired."
- **Aucun message** : "No messages yet! Share your link to receive messages."

### 10.2 Erreurs Système
- **Base de données** : Retry automatique avec fallback
- **API Telegram** : Gestion des rate limits et timeouts
- **Sessions expirées** : Redirection vers l'accueil avec message explicatif
- **Génération de liens** : Nouvelle tentative en cas de collision

### 10.3 Logging et Monitoring
- **Actions utilisateur** : Log de toutes les interactions importantes
- **Erreurs système** : Capture complète avec stack trace
- **Performance** : Monitoring des temps de réponse
- **Alertes** : Notification admin en cas de problèmes critiques

## 11. Processus de Développement

### 11.1 Phase 1 : Infrastructure (1 semaine)
- Configuration PostgreSQL et modèles de données
- Bot Telegram avec structure de base et commandes principales
- Système d'enregistrement et gestion des utilisateurs
- Interface de base avec boutons Play et Inbox

### 11.2 Phase 2 : Système de Liens (1 semaine)
- Génération et validation des liens uniques
- Logique de création de profil utilisateur
- Interface Play avec saisie du nom d'utilisateur
- Système de session pour les processus multi-étapes

### 11.3 Phase 3 : Messages Anonymes (1 semaine)
- Traitement des liens entrants pour envoi de messages
- Interface de saisie et validation des messages
- Stockage des messages anonymes en base
- Notification des destinataires

### 11.4 Phase 4 : Interface Inbox (1 semaine)
- Système de pagination pour l'affichage des messages
- Navigation entre les messages avec boutons
- Fonctionnalité de partage des messages
- Marquage automatique des messages comme lus

### 11.5 Phase 5 : Finalisation et Analytics (1 semaine)
- Système de statistiques et métriques
- Gestion de la suppression de compte
- Jobs de nettoyage et maintenance automatique
- Tests complets et optimisation des performances

## 12. Métriques de Performance

### 12.1 Objectifs de Performance
- **Réponse bot** : < 1 seconde pour les commandes simples
- **Génération de liens** : < 2 secondes incluant validation
- **Affichage messages** : < 1 seconde avec pagination
- **Envoi message anonyme** : < 3 secondes de bout en bout

### 12.2 Métriques d'Usage
- **Utilisateurs actifs quotidiens** : Nombre d'utilisateurs utilisant le bot par jour
- **Messages envoyés/jour** : Volume total de messages anonymes
- **Taux de conversion** : % d'utilisateurs créant un profil après inscription
- **Engagement** : Messages moyen par utilisateur, fréquence d'utilisation

### 12.3 Disponibilité
- **Uptime** : 99.9% de disponibilité cible
- **Temps de récupération** : < 5 minutes en cas de problème
- **Monitoring** : Vérification continue des services critiques
- **Backup** : Sauvegarde quotidienne des données

## 13. Cas d'Usage Principaux

### 13.1 Nouvel Utilisateur
1. Découverte du bot via partage ou recherche
2. Première interaction avec `/start`
3. Exploration de l'interface avec les boutons Play/Inbox
4. Activation du mode Play et création du profil
5. Partage du lien sur les réseaux sociaux
6. Réception des premiers messages anonymes
7. Consultation régulière de l'inbox

### 13.2 Utilisateur Envoyant un Message
1. Réception d'un lien partagé par un ami
2. Clic sur le lien ouvrant le bot
3. Saisie du message anonyme
4. Confirmation d'envoi
5. Possibilité d'envoyer d'autres messages

### 13.3 Utilisateur Actif
1. Consultation quotidienne de l'inbox
2. Partage des messages intéressants reçus
3. Mise à jour occasionnelle du nom d'utilisateur
4. Suivi des statistiques personnelles
5. Partage du lien sur différentes plateformes

Cette documentation fournit une base complète pour le développement de WhisperBot, un bot Telegram d'messages anonymes simple et efficace. L'architecture modulaire et les spécifications détaillées permettront une implémentation robuste tout en maintenant une expérience utilisateur fluide et intuitive.