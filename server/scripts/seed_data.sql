-- =============================================
-- 工作流定义数据填充脚本
-- =============================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- =============================================
-- workflow_definitions
-- =============================================

INSERT IGNORE INTO workflow_definitions (id, name, description, entry_point, human_in_the_loop, config) VALUES
(1, 'simple_router', '简单路由工作流：根据输入自动路由到搜索、计算或天气节点', 'router', NULL, NULL),
(2, 'approval', '自动化审批工作流：支持自动审批和人工审批（Human-in-the-Loop）', 'submit', NULL, NULL);

-- =============================================
-- workflow_definition_nodes - simple_router
-- =============================================

INSERT IGNORE INTO workflow_definition_nodes (workflow_id, node_id, node_type, label, handler, position_x, position_y, config) VALUES
(1, 'router', 'router', '路由节点', 'router', 400, 50, '{"routing_mode": "llm_or_rule", "description": "分析输入，决定路由到哪个处理节点"}'),
(1, 'search', 'tool', '搜索', 'search', 100, 250, '{"description": "搜索信息、查找资料"}'),
(1, 'calculate', 'tool', '计算', 'calculate', 300, 250, '{"description": "数学计算、算术运算"}'),
(1, 'weather', 'tool', '天气', 'weather', 500, 250, '{"description": "天气查询、气温预报"}'),
(1, 'unknown', 'unknown', '未知请求', 'unknown', 700, 250, '{"description": "无法识别的请求"}');

-- =============================================
-- workflow_definition_nodes - approval
-- =============================================

INSERT IGNORE INTO workflow_definition_nodes (workflow_id, node_id, node_type, label, handler, position_x, position_y, config) VALUES
(2, 'submit', 'processor', '提交申请', 'submit', 400, 50, '{"description": "验证请求并生成请求 ID"}'),
(2, 'evaluate', 'processor', '自动评估', 'evaluate', 400, 200, '{"description": "基于规则评估风险等级和推荐动作"}'),
(2, 'auto_approve', 'processor', '自动审批', 'auto_approve', 200, 350, '{"description": "低风险请求自动通过"}'),
(2, 'human_approval', 'router', '人工审批', 'human_approval', 600, 350, '{"description": "中高风险请求等待人工审批（Human-in-the-Loop）"}'),
(2, 'notify', 'processor', '发送通知', 'notify', 400, 500, '{"description": "发送审批结果通知"}');

-- =============================================
-- workflow_definition_edges - simple_router
-- =============================================

INSERT IGNORE INTO workflow_definition_edges (workflow_id, edge_id, source, target, edge_type, condition_field, condition_operator, condition_value) VALUES
(1, 'e-router-search', 'router', 'search', 'conditional', 'route', '==', 'search'),
(1, 'e-router-calculate', 'router', 'calculate', 'conditional', 'route', '==', 'calculate'),
(1, 'e-router-weather', 'router', 'weather', 'conditional', 'route', '==', 'weather'),
(1, 'e-router-unknown', 'router', 'unknown', 'conditional', 'route', '==', 'unknown'),
(1, 'e-search-end', 'search', '__end__', 'normal', NULL, NULL, NULL),
(1, 'e-calculate-end', 'calculate', '__end__', 'normal', NULL, NULL, NULL),
(1, 'e-weather-end', 'weather', '__end__', 'normal', NULL, NULL, NULL),
(1, 'e-unknown-end', 'unknown', '__end__', 'normal', NULL, NULL, NULL);

-- =============================================
-- workflow_definition_edges - approval
-- =============================================

INSERT IGNORE INTO workflow_definition_edges (workflow_id, edge_id, source, target, edge_type, condition_field, condition_operator, condition_value) VALUES
(2, 'e-submit-evaluate', 'submit', 'evaluate', 'normal', NULL, NULL, NULL),
(2, 'e-evaluate-auto', 'evaluate', 'auto_approve', 'conditional', 'recommended_action', '==', 'auto_approve'),
(2, 'e-evaluate-human', 'evaluate', 'human_approval', 'conditional', 'recommended_action', '!=', 'auto_approve'),
(2, 'e-auto-notify', 'auto_approve', 'notify', 'normal', NULL, NULL, NULL),
(2, 'e-human-notify', 'human_approval', 'notify', 'conditional', 'final_status', 'in', 'approved,rejected'),
(2, 'e-human-end', 'human_approval', '__end__', 'conditional', 'final_status', 'not_in', 'approved,rejected'),
(2, 'e-notify-end', 'notify', '__end__', 'normal', NULL, NULL, NULL);

-- =============================================
-- workflow_state_fields - simple_router
-- =============================================

INSERT IGNORE INTO workflow_state_fields (workflow_id, field_name, field_type, field_index) VALUES
(1, 'input', 'str', 0),
(1, 'route', 'str', 1),
(1, 'output', 'str', 2),
(1, 'error', 'Optional[str]', 3),
(1, 'routing_reasoning', 'Optional[str]', 4),
(1, 'routing_confidence', 'Optional[float]', 5);

-- =============================================
-- workflow_state_fields - approval
-- =============================================

INSERT IGNORE INTO workflow_state_fields (workflow_id, field_name, field_type, field_index) VALUES
(2, 'messages', 'list', 0),
(2, 'request', 'dict', 1),
(2, 'approval_level', 'str', 2),
(2, 'approval_status', 'str', 3),
(2, 'auto_evaluation', 'dict', 4),
(2, 'risk_level', 'str', 5),
(2, 'recommended_action', 'str', 6),
(2, 'approval_history', 'list', 7),
(2, 'requires_human', 'bool', 8),
(2, 'human_approved', 'Optional[bool]', 9),
(2, 'human_comments', 'Optional[str]', 10),
(2, 'approver_id', 'Optional[str]', 11),
(2, 'final_status', 'str', 12),
(2, 'final_decision', 'str', 13),
(2, 'notification_sent', 'bool', 14),
(2, 'error', 'Optional[str]', 15);

SET FOREIGN_KEY_CHECKS = 1;

-- =============================================
-- 验证数据
-- =============================================

SELECT 'workflow_definitions' AS table_name, COUNT(*) AS count FROM workflow_definitions
UNION ALL
SELECT 'workflow_definition_nodes' AS table_name, COUNT(*) AS count FROM workflow_definition_nodes
UNION ALL
SELECT 'workflow_definition_edges' AS table_name, COUNT(*) AS count FROM workflow_definition_edges
UNION ALL
SELECT 'workflow_state_fields' AS table_name, COUNT(*) AS count FROM workflow_state_fields;