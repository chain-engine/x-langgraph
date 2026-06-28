-- x-langgraph MySQL 初始化脚本
-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS `x-langgraph`
    DEFAULT CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE `x-langgraph`;

-- LangGraph Checkpoint 表会由 langgraph-checkpoint-mysql 自动创建
-- 这里只需要确保数据库存在即可

-- 授权（可选，根据需要调整）
-- GRANT ALL PRIVILEGES ON `x-langgraph`.* TO 'root'@'%';
-- FLUSH PRIVILEGES;
