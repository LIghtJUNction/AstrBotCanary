from typing import Any, Generic, TypeVar

from astrbot_injector import Depends, DependencyGraph, ParamInfo


def test_sync_basic_resolution() -> None:
	def dep1() -> int:
		return 1

	def target_func(some_int: int = Depends(dep1)) -> int:
		return some_int + 1

	graph = DependencyGraph(target_func)
	with graph.sync_ctx() as ctx:
		kwargs = ctx.resolve_kwargs()
		assert kwargs["some_int"] == 1
		assert target_func(**kwargs) == 2


def test_paraminfo_passed_to_dependency() -> None:
	# dependency that expects ParamInfo
	def dependency(info: ParamInfo = Depends()) -> str:
		# name should be the parameter name in the outer function
		assert info.name == "dd"
		return info.name

	def target_func(dd: str = Depends(dependency)) -> str:
		return dd

	graph = DependencyGraph(target_func)
	with graph.sync_ctx() as ctx:
		kwargs = ctx.resolve_kwargs()
		# resolved value should be the parameter name returned from dependency
		assert kwargs["dd"] == "dd"


def test_replaced_dependency_runtime() -> None:
	def dependency() -> int:
		return 1

	def replaced() -> int:
		return 2

	def target(dep_value: int = Depends(dependency)) -> int:
		return dep_value

	graph = DependencyGraph(target)
	# replace dependency at runtime
	with graph.sync_ctx(replaced_deps={dependency: replaced}) as ctx:
		kwargs = ctx.resolve_kwargs()
		assert kwargs["dep_value"] == 2


def test_generics_class_dependency() -> None:
	# Minimal generic example from project description
	import abc

	class MyInterface(abc.ABC):
		@abc.abstractmethod
		def getval(self) -> Any:  # pragma: no cover - abstract
			...


	_T = TypeVar("_T", bound=MyInterface)


	class MyClass(Generic[_T]):
		def __init__(self, resource: _T = Depends()):
			self.resource = resource

		@property
		def my_value(self) -> Any:
			return self.resource.getval()


	def getstr() -> str:
		return "strstr"


	def getint() -> int:
		return 100


	class MyDep1(MyInterface):
		def __init__(self, s: str = Depends(getstr)) -> None:
			self.s = s

		def getval(self) -> str:
			return self.s


	class MyDep2(MyInterface):
		def __init__(self, i: int = Depends(getint)) -> None:
			self.i = i

		def getval(self) -> int:
			return self.i


	def my_target(
		d1: MyClass[MyDep1] = Depends(),
		d2: MyClass[MyDep2] = Depends(),
	) -> None:
		# simply access properties to ensure everything resolved
		assert d1.my_value == "strstr"
		assert d2.my_value == 100


	graph = DependencyGraph(my_target)
	with graph.sync_ctx() as ctx:
		kwargs = ctx.resolve_kwargs()
		# kwargs should contain instances of MyClass[...] for d1 and d2
		assert isinstance(kwargs["d1"], MyClass)
		assert isinstance(kwargs["d2"], MyClass)
		# calling target with resolved kwargs should not raise
		my_target(**kwargs)

