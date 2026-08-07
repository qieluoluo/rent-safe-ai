from app.core.config import Settings


class DifyWorkflowAdapter:
    """Dify Workflow 的接入占位。

    后续只需在此处将 Dify workflow 的 JSON 输出映射为现有六步结果，
    不影响路由、任务记录和报告落库逻辑。
    """

    def __init__(self, settings: Settings) -> None:
        self.api_base = settings.dify_api_base
        self.api_key = settings.dify_api_key
        self.workflow_id = settings.dify_workflow_id

    def is_configured(self) -> bool:
        return bool(self.api_base and self.api_key and self.workflow_id)
