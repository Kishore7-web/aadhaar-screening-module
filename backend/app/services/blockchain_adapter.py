from ..config import settings

class BlockchainAdapter:
    def __init__(self):
        self.enabled = settings.blockchain_enabled
        self.rpc_url = settings.blockchain_rpc_url

    def status(self):
        if not self.enabled or not self.rpc_url:
            return {"status": "NOT_CONFIGURED", "message": "Blockchain anchoring not configured. Using local tamper-evident hash chain."}
        # Future: connect to RPC
        return {"status": "NOT_AVAILABLE", "message": "Blockchain adapter not connected."}

    def anchor(self, event_hash: str, case_id: str):
        # Placeholder for future blockchain anchoring
        st = self.status()
        if st["status"] != "NOT_CONFIGURED":
            # would anchor
            return {"anchored": False, "tx": None, "status": st["status"]}
        return {"anchored": False, "tx": None, "status": "NOT_CONFIGURED"}

blockchain_adapter = BlockchainAdapter()
