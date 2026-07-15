# -*- coding: utf-8 -*-
"""
工作流实体模型

定义工作流相关的数据表映射。
"""

from datetime import datetime

from sqlalchemy import Column, String, Text, JSON, ForeignKey, DateTime, Integer
from sqlalchemy.orm import relationship

from .base import Base


class WorkflowInstance(Base):
    """
    工作流实例实体

    存储工作流的运行时状态和元数据。
    """

    __tablename__ = "workflow_instances"

    workflow_name = Column(String(100), nullable=False, comment="工作流名称")
    thread_id = Column(String(64), unique=True, nullable=False, comment="会话 ID")
    status = Column(String(20), default="running", comment="状态")
    checkpoint = Column(JSON, nullable=True, comment="检查点数据")
    instance_metadata = Column(JSON, nullable=True, comment="元数据")


class WorkflowNode(Base):
    """
    工作流节点实体

    存储工作流执行过程中的节点信息。
    """

    __tablename__ = "workflow_nodes"

    workflow_instance_id = Column(Integer, ForeignKey("workflow_instances.id"), comment="工作流实例 ID")
    node_name = Column(String(100), nullable=False, comment="节点名称")
    node_type = Column(String(50), nullable=False, comment="节点类型")
    input_data = Column(JSON, nullable=True, comment="输入数据")
    output_data = Column(JSON, nullable=True, comment="输出数据")
    status = Column(String(20), default="pending", comment="状态")

    workflow_instance = relationship("WorkflowInstance", backref="nodes")


class WorkflowExecution(Base):
    """
    工作流执行记录实体

    存储工作流的执行历史记录。
    """

    __tablename__ = "workflow_executions"

    workflow_instance_id = Column(Integer, ForeignKey("workflow_instances.id"), comment="工作流实例 ID")
    step = Column(Integer, nullable=False, comment="执行步骤")
    node_name = Column(String(100), nullable=False, comment="执行节点名称")
    timestamp = Column(DateTime, nullable=False, comment="执行时间")
    result = Column(JSON, nullable=True, comment="执行结果")
    error = Column(Text, nullable=True, comment="错误信息")

    workflow_instance = relationship("WorkflowInstance", backref="executions")
