export function roleLabel(role: string, translate: (key: string) => string) {
  if (role === 'ADMIN') {
    return translate('access:roleAdmin')
  }
  if (role === 'TEACHER') {
    return translate('access:roleTeacher')
  }
  if (role === 'STUDENT') {
    return translate('access:roleStudent')
  }
  return role
}
