-- ============================================================
-- 租安AI 数据库建表脚本
-- 数据库：MySQL 8.0+
-- 字符集：utf8mb4（支持emoji和中文）
-- ============================================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS `rent_safe_ai`
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE `rent_safe_ai`;

-- ============================================================
-- 1. 用户表（无外键依赖，最先建）
-- ============================================================
DROP TABLE IF EXISTS `user`;
CREATE TABLE `user` (
    `id`          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '用户ID',
    `username`    VARCHAR(50)  NOT NULL COMMENT '用户名',
    `password`    VARCHAR(255) NOT NULL COMMENT '密码（加密存储）',
    `phone`       VARCHAR(20)  DEFAULT NULL COMMENT '手机号',
    `avatar`      VARCHAR(255) DEFAULT NULL COMMENT '头像URL',
    `create_time` DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_username` (`username`),
    KEY `idx_phone` (`phone`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';


-- ============================================================
-- 2. 案件表（依赖user，第二建）
-- ============================================================
DROP TABLE IF EXISTS `case_case`;
CREATE TABLE `case_case` (
    `id`          BIGINT        NOT NULL AUTO_INCREMENT COMMENT '案件ID',
    `user_id`     BIGINT        NOT NULL COMMENT '用户ID',
    `case_title`  VARCHAR(100)  DEFAULT NULL COMMENT '案件名称',
    `case_type`   VARCHAR(50)   NOT NULL COMMENT '纠纷类型：DEPOSIT-押金纠纷/RENT_CANCEL-提前退租/REPAIR-维修责任/CONTRACT-合同风险',
    `status`      VARCHAR(20)   DEFAULT 'CREATED' COMMENT '案件状态：CREATED-已创建/ANALYZING-分析中/WAITING-等待补充/COMPLETED-已完成',
    `description` TEXT          DEFAULT NULL COMMENT '用户纠纷描述',
    `amount`      DECIMAL(10,2) DEFAULT NULL COMMENT '涉及金额',
    `start_date`  DATE          DEFAULT NULL COMMENT '租赁开始时间',
    `end_date`    DATE          DEFAULT NULL COMMENT '租赁结束时间',
    `risk_level`  VARCHAR(20)   DEFAULT NULL COMMENT '风险等级：LOW-低/MEDIUM-中/HIGH-高',
    `ai_status`   VARCHAR(20)   DEFAULT 'PENDING' COMMENT 'AI分析状态：PENDING-待处理/PROCESSING-处理中/DONE-完成/FAILED-失败',
    `create_time` DATETIME      DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    KEY `idx_user_id` (`user_id`),
    KEY `idx_case_type` (`case_type`),
    KEY `idx_status` (`status`),
    CONSTRAINT `fk_case_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='案件表';


-- ============================================================
-- 3. 证据表（依赖case_case，第三建）
-- ============================================================
DROP TABLE IF EXISTS `evidence`;
CREATE TABLE `evidence` (
    `id`               BIGINT       NOT NULL AUTO_INCREMENT COMMENT '证据ID',
    `case_id`          BIGINT       NOT NULL COMMENT '案件ID',
    `file_name`        VARCHAR(255) DEFAULT NULL COMMENT '文件名称',
    `file_url`         VARCHAR(500) DEFAULT NULL COMMENT '文件存储地址',
    `file_type`        VARCHAR(50)  DEFAULT NULL COMMENT '文件格式：pdf/png/jpg/mp4等',
    `evidence_type`    VARCHAR(50)  DEFAULT NULL COMMENT '证据分类：CONTRACT-合同/PAYMENT-支付/CHAT-聊天/IMAGE-照片/VIDEO-视频/OTHER-其他',
    `ai_summary`       TEXT         DEFAULT NULL COMMENT 'AI生成的证据摘要',
    `importance_level` VARCHAR(20)  DEFAULT NULL COMMENT '重要程度：HIGH-重要/MEDIUM-一般/LOW-低价值',
    `extract_content`  TEXT         DEFAULT NULL COMMENT 'AI提取的关键信息（JSON格式）',
    `upload_time`      DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
    PRIMARY KEY (`id`),
    KEY `idx_case_id` (`case_id`),
    KEY `idx_evidence_type` (`evidence_type`),
    CONSTRAINT `fk_evidence_case` FOREIGN KEY (`case_id`) REFERENCES `case_case` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='证据表';


-- ============================================================
-- 4. AI分析报告表（依赖case_case，第四建）
-- ============================================================
DROP TABLE IF EXISTS `ai_report`;
CREATE TABLE `ai_report` (
    `id`               BIGINT      NOT NULL AUTO_INCREMENT COMMENT '报告ID',
    `case_id`          BIGINT      NOT NULL COMMENT '案件ID',
    `version`          INT         DEFAULT 1 COMMENT '报告版本号，补充证据后递增',
    `summary`          TEXT        DEFAULT NULL COMMENT '纠纷事实摘要',
    `risk_analysis`    TEXT        DEFAULT NULL COMMENT '风险评估：等级+原因',
    `legal_basis`      TEXT        DEFAULT NULL COMMENT '法律依据：引用的法条',
    `missing_evidence` TEXT        DEFAULT NULL COMMENT '缺失证据提示',
    `action_plan`      TEXT        DEFAULT NULL COMMENT '行动建议：下一步操作步骤',
    `disclaimer`       TEXT        DEFAULT NULL COMMENT '产品边界与免责声明',
    `provider`         VARCHAR(50) DEFAULT NULL COMMENT 'mock/openai-compatible',
    `ai_model`         VARCHAR(100) DEFAULT NULL COMMENT '使用的AI模型名称',
    `prompt_version`   VARCHAR(50) DEFAULT NULL COMMENT 'Prompt版本',
    `knowledge_version` VARCHAR(100) DEFAULT NULL COMMENT '知识库版本',
    `token_usage`      INT         DEFAULT NULL COMMENT '本次生成消耗的token数',
    `create_time`      DATETIME    DEFAULT CURRENT_TIMESTAMP COMMENT '生成时间',
    PRIMARY KEY (`id`),
    KEY `idx_case_id` (`case_id`),
    UNIQUE KEY `uk_case_version` (`case_id`, `version`),
    CONSTRAINT `fk_report_case` FOREIGN KEY (`case_id`) REFERENCES `case_case` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI分析报告表';


-- ============================================================
-- 5. AI任务记录表（依赖case_case，最后建）
-- ============================================================
DROP TABLE IF EXISTS `ai_task`;
CREATE TABLE `ai_task` (
    `id`          BIGINT      NOT NULL AUTO_INCREMENT COMMENT '任务ID',
    `case_id`     BIGINT      NOT NULL COMMENT '案件ID',
    `task_type`   VARCHAR(50) NOT NULL COMMENT '任务类型：INTENT/EXTRACT/COMPLETENESS/KNOWLEDGE/RISK/REPORT',
    `prompt`      TEXT        DEFAULT NULL COMMENT '输入Prompt完整内容',
    `response`    TEXT        DEFAULT NULL COMMENT 'AI输出结果',
    `status`      VARCHAR(20) DEFAULT 'PENDING' COMMENT '任务状态：PENDING-待执行/RUNNING-执行中/SUCCESS-成功/FAILED-失败',
    `latency`     INT         DEFAULT NULL COMMENT '耗时（毫秒）',
    `provider`    VARCHAR(50) DEFAULT NULL COMMENT '模型供应方或mock',
    `model`       VARCHAR(100) DEFAULT NULL COMMENT '精确模型或规则基线名称',
    `prompt_version` VARCHAR(50) DEFAULT NULL COMMENT 'Prompt版本',
    `knowledge_version` VARCHAR(100) DEFAULT NULL COMMENT '知识库版本',
    `token_usage` INT DEFAULT NULL COMMENT '任务token消耗',
    `error_type`  VARCHAR(100) DEFAULT NULL COMMENT '失败类型',
    `create_time` DATETIME    DEFAULT CURRENT_TIMESTAMP COMMENT '执行时间',
    PRIMARY KEY (`id`),
    KEY `idx_case_id` (`case_id`),
    KEY `idx_task_type` (`task_type`),
    KEY `idx_status` (`status`),
    CONSTRAINT `fk_task_case` FOREIGN KEY (`case_id`) REFERENCES `case_case` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI任务记录表';


-- ============================================================
-- 建表完成验证
-- ============================================================
-- 查看所有表
SHOW TABLES;

-- 预期输出：
-- ai_report
-- ai_task
-- case_case
-- evidence
-- user

-- 查看表结构
-- DESCRIBE case_case;
-- DESCRIBE evidence;
-- DESCRIBE ai_report;
-- DESCRIBE ai_task;
