import pydantic
import pydantic.json_schema
import pydantic_core


class OpenAPIDocsEnumMixin:
    """Adjust enum for better support of openapi."""

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: pydantic_core.core_schema.CoreSchema,
        handler: pydantic.GetJsonSchemaHandler,
    ) -> pydantic.json_schema.JsonSchemaValue:
        """Adjust enum for openapi schema.

        Add names x-enum-varnames for better support of codegen.

        """
        generated_schema = handler(core_schema)
        generated_schema = handler.resolve_ref_schema(generated_schema)
        generated_schema["x-enum-varnames"] = [
            choice.name
            for choice in cls  # type: ignore
        ]
        return generated_schema
