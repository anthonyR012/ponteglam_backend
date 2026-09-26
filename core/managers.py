from django.db import models


class TypeManager(models.Manager):
    """
    Manager for the Type model.
    """

    def get_type(self, code, category_type_code):
        """
        Retrieve a type based on the provided code and category type code.

        Args:
            code (str): The code used to identify the type.
            category_type_code (str): The code of the category type.

        Returns:
            The retrieved type.
        """
        type = self.get(
            code=code, category_type__code=category_type_code
        )
        return type
