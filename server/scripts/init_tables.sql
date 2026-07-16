-- =============================================
-- x-langgraph 数据库初始化脚本
-- =============================================

-- 工作流定义表
CREATE TABLE IF NOT EXISTS workflow_definitions (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键 ID',
    name VARCHAR(100) NOT NULL UNIQUE COMMENT '工作流名称',
    description TEXT COMMENT '工作流描述',
    entry_point VARCHAR(100) COMMENT '入口节点',
    human_in_the_loop JSON COMMENT '人工介入配置',
    config JSON COMMENT '额外配置',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工作流定义表';

-- 工作流定义节点表
CREATE TABLE IF NOT EXISTS workflow_definition_nodes (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键 ID',
    workflow_id INT NOT NULL COMMENT '工作流定义 ID',
    node_id VARCHAR(100) NOT NULL COMMENT '节点 ID',
    node_type VARCHAR(50) NOT NULL COMMENT '节点类型',
    label VARCHAR(100) NOT NULL COMMENT '节点标签',
    handler VARCHAR(100) NOT NULL COMMENT '处理器名称',
    position_x FLOAT COMMENT '画布位置 X',
    position_y FLOAT COMMENT '画布位置 Y',
    config JSON COMMENT '节点配置',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_workflow_id (workflow_id),
    INDEX idx_node_id (node_id),
    FOREIGN KEY (workflow_id) REFERENCES workflow_definitions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工作流定义节点表';

-- 工作流定义边表
CREATE TABLE IF NOT EXISTS workflow_definition_edges (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键 ID',
    workflow_id INT NOT NULL COMMENT '工作流定义 ID',
    edge_id VARCHAR(100) NOT NULL COMMENT '边 ID',
    source VARCHAR(100) NOT NULL COMMENT '源节点',
    target VARCHAR(100) NOT NULL COMMENT '目标节点',
    edge_type VARCHAR(50) NOT NULL COMMENT '边类型',
    condition_field VARCHAR(100) COMMENT '条件字段',
    condition_operator VARCHAR(20) COMMENT '条件操作符',
    condition_value VARCHAR(200) COMMENT '条件值',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_workflow_id (workflow_id),
    INDEX idx_source (source),
    INDEX idx_target (target),
    FOREIGN KEY (workflow_id) REFERENCES workflow_definitions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工作流定义边表';

-- 工作流状态字段表
CREATE TABLE IF NOT EXISTS workflow_state_fields (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键 ID',
    workflow_id INT NOT NULL COMMENT '工作流定义 ID',
    field_name VARCHAR(100) NOT NULL COMMENT '字段名称',
    field_type VARCHAR(50) NOT NULL COMMENT '字段类型',
    field_index INT DEFAULT 0 COMMENT '字段顺序',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_workflow_id (workflow_id),
    INDEX idx_field_name (field_name),
    FOREIGN KEY (workflow_id) REFERENCES workflow_definitions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工作流状态字段表';

-- 工作流实例表
CREATE TABLE IF NOT EXISTS workflow_instances (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键 ID',
    workflow_name VARCHAR(100) NOT NULL COMMENT '工作流名称',
    thread_id VARCHAR(64) NOT NULL UNIQUE COMMENT '会话 ID',
    status VARCHAR(20) DEFAULT 'running' COMMENT '状态',
    checkpoint JSON COMMENT '检查点数据',
    instance_metadata JSON COMMENT '元数据',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_workflow_name (workflow_name),
    INDEX idx_thread_id (thread_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工作流实例表';

-- 工作流节点执行记录表
CREATE TABLE IF NOT EXISTS workflow_nodes (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键 ID',
    workflow_instance_id INT COMMENT '工作流实例 ID',
    node_name VARCHAR(100) NOT NULL COMMENT '节点名称',
    node_type VARCHAR(50) NOT NULL COMMENT '节点类型',
    input_data JSON COMMENT '输入数据',
    output_data JSON COMMENT '输出数据',
    status VARCHAR(20) DEFAULT 'pending' COMMENT '状态',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_workflow_instance_id (workflow_instance_id),
    FOREIGN KEY (workflow_instance_id) REFERENCES workflow_instances(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工作流节点执行记录表';

-- 工作流执行历史表
CREATE TABLE IF NOT EXISTS workflow_executions (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键 ID',
    workflow_instance_id INT COMMENT '工作流实例 ID',
    step INT NOT NULL COMMENT '执行步骤',
    node_name VARCHAR(100) NOT NULL COMMENT '执行节点名称',
    timestamp DATETIME NOT NULL COMMENT '执行时间',
    result JSON COMMENT '执行结果',
    error TEXT COMMENT '错误信息',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_workflow_instance_id (workflow_instance_id),
    INDEX idx_step (step),
    FOREIGN KEY (workflow_instance_id) REFERENCES workflow_instances(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工作流执行历史表';