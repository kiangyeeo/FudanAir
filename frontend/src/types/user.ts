export interface UserProfile {
  user_id: number
  phone: string
  name: string
}

export interface UserProfileUpdate {
  phone?: string
  name?: string
}

export interface PasswordUpdate {
  old_password: string
  new_password: string
}

export interface Passenger {
  id_no: string
  real_name: string
  birth_date: string
}

export interface PassengerUpdate {
  real_name: string
  birth_date: string
}
