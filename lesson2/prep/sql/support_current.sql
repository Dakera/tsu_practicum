-- Извлечение текущих обращений из SQLite (ноябрь 2025 — август 2026).
-- Все поля хранятся в базе как TEXT и читаются без преобразований:
-- приведение типов и часовых поясов выполняется в Python после аудита сырых значений.
SELECT ticket_id,
       customer_id,
       created_at,
       available_at,
       topic,
       channel,
       resolved_at,
       resolution_available_at,
       satisfaction_score
FROM support_current_raw;
