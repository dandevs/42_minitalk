/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   lib.h                                              :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: danimend <danimend@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/03/29 20:45:17 by danimend          #+#    #+#             */
/*   Updated: 2026/03/30 03:59:38 by danimend         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#ifndef LIB_H
# define LIB_H

# define BUFFER_SIZE 4194304

int		ft_strlen(char *str);
void	ft_write_str(int fd, char *str);
void	ft_putnbr_fd(int fd, int n);

#endif
