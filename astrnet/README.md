"""Astrnet: 集成TaskIQ和Strawberry的简单API框架

Astrnet提供了一个简单的类AstrnetApp，用于将TaskIQ分布式任务调度与Strawberry GraphQL集成，
无需网络端口（使用InMemoryBroker）。

基本用法:

```python
from astrnet import AstrnetApp

app = AstrnetApp()

@app.task
async def add_numbers(a: int, b: int) -> int:
    return a + b

@app.query
async def calculate(a: int, b: int) -> int:
    # 自动调用TaskIQ任务
    return await app.run_task("add_numbers", a, b)

schema = app.create_schema()
```

然后可以执行GraphQL查询:

```python
result = await schema.execute("{ calculate(a: 1, b: 2) }")
print(result.data)  # {'calculate': 3}
```

也可以挂载到FastAPI:

```python
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter

fastapi_app = FastAPI()
graphql_router = app.create_graphql_router(schema)
fastapi_app.include_router(graphql_router, prefix="/graphql")
```
"""
