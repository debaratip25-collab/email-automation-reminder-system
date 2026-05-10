CREATE DATABASE IF NOT EXISTS email_automation;
USE email_automation;

CREATE TABLE IF NOT EXISTS contacts(
  id CHAR(36) PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  email VARCHAR(190) NOT NULL UNIQUE,
  timezone VARCHAR(64) DEFAULT 'Asia/Kolkata',
  unsubscribed BOOLEAN DEFAULT 0
);

CREATE TABLE IF NOT EXISTS templates(
  id CHAR(36) PRIMARY KEY,
  name VARCHAR(120) NOT NULL UNIQUE,
  subject TEXT NOT NULL,
  body_md LONGTEXT NOT NULL,
  created_at DATETIME NOT NULL
);

CREATE TABLE IF NOT EXISTS campaigns(
  id CHAR(36) PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  template_id CHAR(36) NOT NULL,
  sender_name VARCHAR(120) NOT NULL,
  sender_email VARCHAR(190) NOT NULL,
  created_at DATETIME NOT NULL,
  FOREIGN KEY(template_id) REFERENCES templates(id)
);

CREATE TABLE IF NOT EXISTS reminders(
  id CHAR(36) PRIMARY KEY,
  title VARCHAR(190) NOT NULL,
  contact_id CHAR(36) NOT NULL,
  campaign_id CHAR(36) NOT NULL,
  start_at_utc DATETIME NOT NULL,
  rrule TEXT NULL,
  active BOOLEAN DEFAULT 1,
  last_fired_at_utc DATETIME NULL,
  FOREIGN KEY(contact_id) REFERENCES contacts(id),
  FOREIGN KEY(campaign_id) REFERENCES campaigns(id)
);

CREATE TABLE IF NOT EXISTS messages(
  id CHAR(36) PRIMARY KEY,
  campaign_id CHAR(36) NOT NULL,
  contact_id CHAR(36) NOT NULL,
  scheduled_at_utc DATETIME NOT NULL,
  sent_at_utc DATETIME NULL,
  provider_msg_id VARCHAR(255) NULL,
  status VARCHAR(24) NOT NULL,
  subject TEXT NULL,
  body_rendered_html LONGTEXT NULL,
  error LONGTEXT NULL,
  created_at DATETIME NOT NULL,
  FOREIGN KEY(campaign_id) REFERENCES campaigns(id),
  FOREIGN KEY(contact_id) REFERENCES contacts(id)
);

CREATE INDEX idx_messages_sched ON messages(scheduled_at_utc, status);