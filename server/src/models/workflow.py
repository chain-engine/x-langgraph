# -*- coding: utf-8 -*-
"""
工作流实体模型

定义工作流相关的数据表映射。
"""

from datetime import datetime

from sqlalchemy import Column, String, Text, JSON, ForeignKey, DateTime, Integer, Float
from sqlalchemy.orm import relationship

from .base import Base


class WorkflowDefinition(Base):
    """
    工作流定义实体

    存储工作流的基本信息。
    """

    __tablename__ = "workflow_definitions"

    name = Column(String(100), unique=True, nullable=False, comment="工作流名称")
    description = Column(Text, nullable=True, comment="工作流描述")
    entry_point = Column(String(100), nullable=True, comment="入口节点")
    human_in_the_loop = Column(JSON, nullable=True, comment="人工介入配置")
    config = Column(JSON, nullable=True, comment="额外配置")

    nodes = relationship("WorkflowDefinitionNode", back_populates="workflow", cascade="all, delete-orphan")
    edges = relationship("WorkflowDefinitionEdge", back_populates="workflow", cascade="all, delete-orphan")
    state_fields = relationship("WorkflowStateField", back_populates="workflow", cascade="all, delete-orphan")


class WorkflowDefinitionNode(Base):
    """
    工作流定义节点实体

    存储工作流定义中的节点信息。
    """

    __tablename__ = "workflow_definition_nodes"

    workflow_id = Column(Integer, ForeignKey("workflow_definitions.id"), nullable=False, comment="工作流定义 ID")
    node_id = Column(String(100), nullable=False, comment="节点 ID")
    node_type = Column(String(50), nullable=False, comment="节点类型")
    label = Column(String(100), nullable=False, comment="节点标签")
    handler = Column(String(100), nullable=False, comment="处理器名称")
    position_x = Column(Float, nullable=True, comment="画布位置 X")
    position_y = Column(Float, nullable=True, comment="画布位置 Y")
    config = Column(JSON, nullable=True, comment="节点配置")

    workflow = relationship("WorkflowDefinition", back_populates="nodes")


class WorkflowDefinitionEdge(Base):
    """
    工作流定义边实体

    存储工作流定义中的边（节点间连接）信息。
    """

    __tablename__ = "workflow_definition_edges"

    workflow_id = Column(Integer, ForeignKey("workflow_definitions.id"), nullable=False, comment="工作流定义 ID")
    edge_id = Column(String(100), nullable=False, comment="边 ID")
    source = Column(String(100), nullable=False, comment="源节点")
    target = Column(String(100), nullable=False, comment="目标节点")
    edge_type = Column(String(50), nullable=False, comment="边类型")
    condition_field = Column(String(100), nullable=True, comment="条件字段")
    condition_operator = Column(String(20), nullable=True, comment="条件操作符")
    condition_value = Column(String(200), nullable=True, comment="条件值")

    workflow = relationship("WorkflowDefinition", back_populates="edges")


class WorkflowStateField(Base):
    """
    工作流状态字段实体

    存储工作流定义中的状态字段定义。
    """

    __tablename__ = "workflow_state_fields"

    workflow_id = Column(Integer, ForeignKey("workflow_definitions.id"), nullable=False, comment="工作流定义 ID")
    field_name = Column(String(100), nullable=False, comment="字段名称")
    field_type = Column(String(50), nullable=False, comment="字段类型")
    field_index = Column(Integer, default=0, comment="字段顺序")

    workflow = relationship("WorkflowDefinition", back_populates="state_fields")


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

    nodes = relationship("WorkflowNode", backref="workflow_instance", cascade="all, delete-orphan")
    executions = relationship("WorkflowExecution", backref="workflow_instance", cascade="all, delete-orphan")


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