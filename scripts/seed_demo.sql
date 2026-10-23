-- Agent Interview Lab 演示数据:3 个用户、6 条工单。可重复执行。
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS tickets (
  ticket_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  subject TEXT NOT NULL,
  status TEXT NOT NULL
);

INSERT INTO tickets (ticket_id, user_id, subject, status) VALUES
  ('T-1001', 'user_alice', '无法登录', 'open'),
  ('T-1002', 'user_alice', '账单问题', 'closed'),
  ('T-2001', 'user_bob', '密码重置', 'open'),
  ('T-2002', 'user_bob', '发票申请', 'open'),
  ('T-3001', 'user_carol', '权限申请', 'closed'),
  ('T-3002', 'user_carol', '数据导出', 'open')
ON CONFLICT (ticket_id) DO NOTHING;
