from dotenv import load_dotenv
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig, RunnableSequence
from langchain_core.tracers.stdout import ConsoleCallbackHandler
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.core.config import settings
from app.core.exception import ChainError
from app.core.logging import LogLevel, log
from app.core.utils.datetime_utils import get_current_time
from app.infrastructure.blob_manager.base import BaseBlobManager
from app.infrastructure.llm_chain.base import BaseChain
from app.infrastructure.llm_chain.enums import OpenAIModelName

load_dotenv()


class BaseOpenAIChain(BaseChain):
    def __init__(
        self,
        model_name: OpenAIModelName,
        blob_manager: BaseBlobManager,
        log_level: LogLevel,
        prompt_path: str,
    ) -> None:
        self.model_name = model_name
        self.blob_manager = blob_manager
        self.prompt_path = prompt_path
        super().__init__(log_level)

    def _build_structured_chain(
        self,
        schema: BaseModel,
        temperature: float = 0.0,
    ) -> RunnableSequence:
        llm = ChatOpenAI(model_name=self.model_name.value, temperature=temperature)
        template = self.blob_manager.read_blob_as_str(self.prompt_path)
        prompt = ChatPromptTemplate.from_template(template, template_format="jinja2")
        return prompt | llm.with_structured_output(schema, method="function_calling")  # type: ignore

    def _build_chain(self, temperature: float = 0.0) -> RunnableSequence:
        llm = ChatOpenAI(model_name=self.model_name.value, temperature=temperature)
        template = self.blob_manager.read_blob_as_str(self.prompt_path)
        prompt = ChatPromptTemplate.from_template(template, template_format="jinja2")
        return prompt | llm | StrOutputParser()  # type: ignore

    @property
    def global_instruction(self) -> str:
        template = self.blob_manager.read_blob_as_template(
            settings.GLOBAL_INSTRUCTION_PATH
        )
        return template.render(current_date=get_current_time())

    def invoke(
        self,
        chain: RunnableSequence,
        inputs: dict,
        verbose: bool = False,
    ) -> str | BaseModel:
        callbacks: list[BaseCallbackHandler] = []
        if verbose:
            callbacks.append(ConsoleCallbackHandler())
        config = RunnableConfig(callbacks=callbacks)
        try:
            inputs["global_instruction"] = self.global_instruction
            response = chain.invoke(inputs, config=config)
            log(
                LogLevel.DEBUG,
                subject=self.__name__,
                object="invoke",
                message=response,
            )
            return response  # type: ignore  # noqa: TRY300
        except Exception as e:
            error_message = f"An error occurred while calling the LLM: {e!s}"
            self.log(object="invoke", message=error_message)
            raise ChainError(self.__name__, error_message) from e
