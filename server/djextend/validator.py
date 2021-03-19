import re
from django.core.validators import RegexValidator

# User email
validate_staff_email = RegexValidator(
    regex=re.compile(r'\w+@gmail.com'),
    message='请输入有效的公司邮箱'
)


if __name__ == '__main__':
    print(validate_staff_email.regex)
    print(validate_staff_email(f'abc@def.com'))
    print(validate_staff_email(f'abc@gmail.com'))
