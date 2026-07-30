# -*- coding: utf-8 -*-
"""
枚举基类模块

提供可描述枚举基类，支持标记值和描述信息的枚举类型。
"""

from enum import Enum
from typing import Any


class BaseEnum(Enum):
    """
    可描述枚举基类

    支持标记值和描述信息的枚举类型。
    - mark: 唯一标识
    - desc: 描述信息

    支持两种定义方式：
    1. 类方式：class MyEnum(BaseEnum):
           NAME = ("name", "描述")      # tuple: (mark, desc)
           NAME = "name"                 # str: mark，desc 为空
    2. 函数式：BaseEnum("Name", [...])  # 同级别调用
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._mark: str | int = ""
        self._desc: str = ""
        self._parse_value()

    def _parse_value(self) -> None:
        """从 value 中解析 mark 和 desc"""
        raw = self.value
        if isinstance(raw, tuple) and len(raw) >= 2:
            self._mark = raw[0]
            self._desc = raw[1]
        elif isinstance(raw, str):
            self._mark = raw
            self._desc = ""
        elif isinstance(raw, int):
            self._mark = raw
            self._desc = ""
        else:
            self._mark = str(raw)
            self._desc = ""

    @property
    def mark(self) -> str | int:
        """获取唯一标识"""
        return self._mark

    @property
    def desc(self) -> str:
        """获取描述信息"""
        return self._desc

    def __str__(self) -> str:
        return str(self._mark)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Enum):
            return super().__eq__(other)
        if isinstance(other, str):
            return self._mark == other
        if isinstance(other, int):
            return self._mark == other
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._mark)

    @classmethod
    def get_all_marks(cls) -> list[str | int]:
        """获取所有标记值列表"""
        return [member.mark for member in cls]

    @classmethod
    def get_all_descs(cls) -> list[str]:
        """获取所有描述列表"""
        return [member.desc for member in cls]

    @classmethod
    def get_choices(cls) -> tuple[tuple[str | int, str], ...]:
        """获取选择项列表，用于表单选项"""
        return tuple((member.mark, member.desc) for member in cls)

    @classmethod
    def from_mark(cls, mark: str | int) -> "BaseEnum":
        """根据标记值获取枚举成员"""
        for member in cls:
            if member.mark == mark:
                return member
        raise ValueError(f"Invalid mark: {mark}")

    @classmethod
    def is_valid(cls, mark: str | int) -> bool:
        """检查标记值是否有效"""
        return any(member.mark == mark for member in cls)
